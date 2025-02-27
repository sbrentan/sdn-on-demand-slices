const API_BASE_URL = 'http://localhost:8086/api';
const GUI_BASE_URL = 'http://localhost:8086/gui/';

/* ---------------------- Global variable ---------------------- */

const HOST_COLOR = "#4682B4";
const SWITCH_COLOR = "#FF6347";

var data = undefined;
var ratio = 1.25;

/* ----------------------- Onload helper ----------------------- */

document.addEventListener("DOMContentLoaded", async () => {

    document.getElementById("network-graph").style.transform = `scale(${ratio})`;

    // Default data structure
    const defaultData = {
        nodes: await getNodes(),
        links: await getLinks()
    };

    const slices = await getSlices();

    const sliceList = document.getElementById("slice-list");
    slices.forEach((slice, index) => {
        const li = document.createElement("li");
        li.className = "list-group-item d-flex align-items-center";
        const span = document.createElement("span");
        span.className = "mr-2 slice-color"
        span.style.backgroundColor = getRandomColor();
        li.appendChild(span);
        const sliceText = document.createElement("span");
        sliceText.className = "slice-text";
        sliceText.textContent = `${slice.name} (${slice.min_rate} - ${slice.max_rate})`;
        li.appendChild(sliceText);
        li.dataset.index = index;
        sliceList.appendChild(li);
    });

    // Retrieve saved layout from cookie
    const savedLayout = getCookie("networkLayout");
    data = savedLayout ? JSON.parse(savedLayout) : defaultData;

    renderGraph(data, slices);
});

function getRandomColor() {
    var letters = '0123456789ABCDEF';
    var color = '#';
    for (var i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

function renderGraph(data, slices) {
    
    const width = document.getElementById("network-graph").clientWidth;
    const height = document.getElementById("network-graph").clientHeight;

    const svg = d3.select("#network-graph")
        .attr("viewBox", `0 0 ${width} ${height}`);

    const simulation = d3.forceSimulation(data.nodes)
        .force("link", d3.forceLink(data.links).id(d => d.id).distance(100))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(data.links)
        .enter()
        .append("line")
        .attr("stroke", "#aaa");
    
    const node = svg.append("g")
        .attr("class", "nodes")
        .selectAll("circle")
        .data(data.nodes)
        .enter()
        .append("circle")
        .attr("r", 10)
        .attr("fill", d => d.type === "Host" ? HOST_COLOR : SWITCH_COLOR)
        .attr("stroke", "none") // Default state (no outline)
        .attr("stroke-width", 2)
        .call(drag(simulation))
        .on("click", function(event, d) {
            event.stopPropagation();

            console.log("Clicked node:", d);
    
            // Remove outline from all circles first
            node.attr("stroke", "none");
    
            // Highlight the clicked circle
            d3.select(this)
                .attr("stroke", "#4D90FE")
                .attr("stroke-width", 3);
        }); 

    const label = svg.append("g")
        .attr("class", "labels")
        .selectAll("text")
        .data(data.nodes)
        .enter()
        .append("text")
        .attr("dy", -15)
        .attr("text-anchor", "middle")
        .text(d => d.id);

    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);

        label
            .attr("x", d => d.x)
            .attr("y", d => d.y);
    });

    function drag(simulation) {
        return d3.drag()
            .on("start", event => {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            })
            .on("drag", event => {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            })
            .on("end", event => {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            });
    }

    const sliceList = document.getElementById("slice-list");
    sliceList.addEventListener("click", event => {
        let target = event.target;
        if (event.target.tagName === "SPAN") target = event.target.parentElement;
        console.log(target.dataset.index);
        const selectedSlice = slices[target.dataset.index];
        highlightSlice(target, selectedSlice);
    });

    function highlightSlice(component, slice) {
        const sliceColor = component.querySelector(".slice-color").style.backgroundColor;
        node.attr("fill", d => slice.nodes.includes(d.id) ? sliceColor : d.type === "Host" ? HOST_COLOR : SWITCH_COLOR);
        link.attr("stroke", d => slice.links.includes(d.id) ? sliceColor : "#aaa");
    }
}

/* ----------------------- Cookie helper ----------------------- */

function setCookie(name, value, days) {
    const expires = new Date();
    expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = `${name}=${encodeURIComponent(value)};expires=${expires.toUTCString()};path=/`;
}

function getCookie(name) {
    const cookies = document.cookie.split("; ");
    for (const cookie of cookies) {
        const [key, value] = cookie.split("=");
        if (key === name) {
            return decodeURIComponent(value);
        }
    }
    return null;
}

/* ----------------------- Graph Controls ----------------------- */

function increaseZoom() { 
    if (ratio < 2) {
        ratio += 0.1;
        document.getElementById("network-graph").style.transform = `scale(${ratio})`;
    }
}

function decreaseZoom() {
    if (ratio > 0.5) { 
        ratio -= 0.1;
        document.getElementById("network-graph").style.transform = `scale(${ratio})`;
    }
}

function resetZoom() {
    ratio = 1.25;
    document.getElementById("network-graph").style.transform = `scale(${ratio})`;
}

function saveLayout() {
    if (data !== undefined) {
        const layout = data.nodes.map(node => ({
            id: node.id,
            type: node.type,
            x: node.x,
            y: node.y
        }));
        const links = data.links.map(link => ({
            id: link.id,
            source: link.source.id,
            target: link.target.id
        }));
        const layoutJSON = JSON.stringify({ nodes: layout, links });
        // console.log(layoutJSON);
        setCookie("networkLayout", layoutJSON, 7); // Save for 7 days
        alert("Layout saved!");
    }
}

/* -------------------------------------------------------------- */

async function fetchComponent(component, method = 'GET') {
    try {
        const response = await fetch(GUI_BASE_URL + component, { method });
        if (!response.ok) {
            throw new Error(`Error: ${response.status} - ${response.statusText}`);
        }

        return await response.text();
    } catch (error) {
        console.error(`Failed to fetch component ${component}:`, error);
        throw error;
    }
}

async function loadComponent(component, targetId) {
    try {
        const componentHtml = await fetchComponent(component);
        document.getElementById(targetId).innerHTML = componentHtml;
    } catch (error) {
        console.error(`Failed to load component ${component}:`, error);
    }
}

// Generic function to fetch data from an endpoint
async function fetchData(endpoint, method = 'GET', body = null) {
    try {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(API_BASE_URL + endpoint, options);
        if (!response.ok) {
            throw new Error(`Error: ${response.status} - ${response.statusText}`);
        }

        response_json = await response.json();
        console.log('Response json:', JSON.stringify(response_json, null, 2));
        return response_json
    } catch (error) {
        console.error(`Failed to fetch data from ${endpoint}:`, error);
        throw error;
    }
}

// Fetch slices
async function getSlices() {
    return await fetchData('/slices');
}

// Create a new slice
async function createSlice(sliceData) {
    return await fetchData('/slices', 'POST', sliceData);
}

// Update a slice
async function updateSlice(sliceData) {
    return await fetchData('/slices', 'PUT', sliceData);
}

// Delete a slice
async function deleteSlice(sliceId) {
    return await fetchData('/slices', 'DELETE', { id: sliceId });
}

// Fetch nodes
async function getNodes() {
    return await fetchData('/topology/nodes');
}

// Fetch links
async function getLinks() {
    return await fetchData('/topology/links');
}