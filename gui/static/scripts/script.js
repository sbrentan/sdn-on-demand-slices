const API_BASE_URL = 'http://localhost:8086/api';
const GUI_BASE_URL = 'http://localhost:8086/gui/';

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

document.addEventListener("DOMContentLoaded", async () => {
    // Default data structure
    const defaultData = {
        nodes: await getNodes(),
        links: await getLinks()
    };

    const slices = await getSlices();

    console.log("nodes", defaultData.nodes)
    console.log("link", defaultData.links)
    console.log("slices", slices)

    const sliceList = document.getElementById("slice-list");
    slices.forEach((slice, index) => {
        const li = document.createElement("li");
        li.textContent = `${slice.name} (${slice.min_rate} - ${slice.max_rate})`;
        li.dataset.index = index;
        sliceList.appendChild(li);
    });

    // Retrieve saved layout from cookie
    const savedLayout = getCookie("networkLayout");
    const data = savedLayout ? JSON.parse(savedLayout) : defaultData;

    const ratio = 0.8;
    const width = document.getElementById("network-graph").clientWidth * ratio;
    const height = document.getElementById("network-graph").clientHeight * ratio;

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
        .attr("fill", d => d.type === "Host" ? "blue" : "green")
        .call(drag(simulation));

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

    sliceList.addEventListener("click", event => {
        if (event.target.tagName === "LI") {
            const selectedSlice = slices[event.target.dataset.index];
            highlightSlice(selectedSlice);
        }
    });

    function highlightSlice(slice) {
        node.attr("fill", d => slice.nodes.includes(d.id) ? "orange" : d.type === "Host" ? "blue" : "green");
        link.attr("stroke", d => slice.links.includes(d.id) ? "red" : "#aaa");
    }

    // Save layout button event
    document.getElementById("save-layout").addEventListener("click", () => {
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
        console.log(layoutJSON);
        setCookie("networkLayout", layoutJSON, 7); // Save for 7 days
        alert("Layout saved!");
    });

    // Cookie helpers
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
});