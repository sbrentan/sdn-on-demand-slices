const API_BASE_URL = 'http://localhost:8086/api';
const GUI_BASE_URL = 'http://localhost:8086/gui/';

/* ---------------------- Global variable ---------------------- */

const DISABLED_COLOR = "#dc3545";
const ENABLED_COLOR = "#28a745";
const OUTLINE_COLOR = "#FF6347";
const LINK_COLOR = "#aaa";
const NODE_SIZE = 35;

var graph_data = undefined;
var ratio = 1.25;
var outlineFilter = undefined;

/* ----------------------- Onload helper ----------------------- */

document.addEventListener("DOMContentLoaded", async () => {

    document.getElementById("network-graph").style.transform = `scale(${ratio})`;

    // Default data structure
    graph_data = {
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
        span.style.backgroundColor = slice.active ? ENABLED_COLOR : DISABLED_COLOR;
        li.appendChild(span);
        const sliceText = document.createElement("span");
        sliceText.className = "slice-text";
        sliceText.textContent = `${slice.name} [${slice.id}]`;
        li.appendChild(sliceText);
        li.dataset.index = index;
        sliceList.appendChild(li);
    });

    // Retrieve saved layout from cookie
    const savedLayout = getCookie("networkLayout");
    if (savedLayout) {
        // if saved layout exists, use it to get x and y positions of nodes and updated default_data
        const layout = JSON.parse(savedLayout);
        graph_data.nodes.forEach(node => {
            const savedNode = layout.nodes.find(n => n.id === node.id && n.type === node.type);
            if (savedNode) {
                node.x = savedNode.x;
                node.y = savedNode.y;
            }
        });
    }

    renderGraph(graph_data, slices);
});

async function fetchMenuDetails (url) {
    const menu = document.getElementById('details-menu');
    const target = document.getElementById('details-container');
    // add class
    if (menu.classList.contains('closed')) {
        menu.classList.remove('closed');
        menu.classList.add('opened');
        increaseZoom(0.4);
    }

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`Error: ${response.statusText}`);

        // Insert the response into the target element
        target.innerHTML = await response.text();

        // Restore htmx behavior
        htmx.process(target);

        addAfterRequestEventListeners(target);

        // Execute scripts in the response
        const scripts = target.getElementsByTagName('script');
        for (let script of scripts) {
            const newScript = document.createElement('script');
            newScript.textContent = script.textContent;
            document.head.appendChild(newScript).parentNode.removeChild(newScript);
        }
    } catch (error) {
        console.error('Fetch Error:', error);
        target.innerHTML = '<p>Error loading content.</p>';
    }
}

function closeDetailsMenu() {
    
    let menu = document.querySelector('#details-menu');
    menu.classList.add('closed');
    decreaseZoom(0.4);
    menu.classList.remove('opened');
    document.querySelector('#details-container').innerHTML = '';
}

function addAfterRequestEventListeners(target) {
    let edit_buttons = target.querySelectorAll('.slice-actions button');
    edit_buttons.forEach(button => {
        button.addEventListener('htmx:afterRequest', function(event) {
            let response = event.detail.xhr;
            if (response.status === 200 || response.status === 204) {
                window.location.href = window.location.href;
            } else {
                alert('An error occurred while processing your request.');
            }
        });
    });
}

function highlightSlice(component, slice) {
    let node = d3.selectAll("image");
    let link = d3.selectAll("line");

    outlineFilter.select("feFlood").attr("flood-color", OUTLINE_COLOR);
    node.attr("filter", d => slice.nodes.includes(d.id) ? "url(#outlineFilter)" : null);

    // line stroke 4 if link is in slice, else 2
    link.attr("stroke", d => slice.links.includes(d.id) ? OUTLINE_COLOR : LINK_COLOR).attr("stroke-width", d => slice.links.includes(d.id) ? 4 : 2);
}

function deselectAll() {
    d3.selectAll("image").attr("filter", null);
    d3.selectAll("line").attr("stroke", LINK_COLOR).attr("stroke-width", 2);


    // remove selection from all slices
    const sliceList = document.getElementById("slice-list");
    highlightSlice(sliceList, { nodes: [], links: [] });
    const slices = sliceList.querySelectorAll(".list-group-item");
    slices.forEach(slice => slice.classList.remove("selected"));
}

function renderGraph(data, slices) {
    
    const width = document.getElementById("network-graph").clientWidth;
    const height = document.getElementById("network-graph").clientHeight;

    const svg = d3.select("#network-graph")
        .attr("viewBox", `0 0 ${width} ${height}`)
        .on("click", () => {
            // deselectAll();
        });
    
    // define the outline filter for the svg image selection
    const defs = svg.append("defs");
    outlineFilter = defs.append("filter")
        .attr("id", "outlineFilter");

    outlineFilter.append("feMorphology")
        .attr("in", "SourceAlpha")
        .attr("operator", "dilate")
        .attr("radius", "3")
        .attr("result", "dilated");

    outlineFilter.append("feFlood")
        .attr("flood-color", OUTLINE_COLOR)
        .attr("result", "flooded");

    outlineFilter.append("feComposite")
        .attr("in", "flooded")
        .attr("in2", "dilated")
        .attr("operator", "in")
        .attr("result", "outlined");

    const feMerge = outlineFilter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "outlined");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    const simulation = d3.forceSimulation(data.nodes)
        .force("link", d3.forceLink(data.links).id(d => d.id).distance(100))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2));

    simulation.on("tick", () => {
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        // For images, use 'x' and 'y' attributes and adjust by half the image width/height (10)
        node
            .attr("x", d => d.x - 15)
            .attr("y", d => d.y - 15);

        label
            .attr("x", d => d.x)
            .attr("y", d => d.y);
    });

    const link = svg.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(data.links)
        .enter()
        .append("line")
        .attr("stroke", LINK_COLOR)
        .attr("stroke-width", 2)
        .attr("cursor", "pointer")
        .on("mouseover", function() {
            d3.select(this).attr("stroke-width", 4);
        })
        .on("mouseout", function() {
            if (d3.select(this).attr("stroke") === LINK_COLOR) {
                d3.select(this).attr("stroke-width", 2);
            }
        })
        .on("click", function(event, d) {
            event.stopPropagation();

            deselectAll();

            // Highlight the clicked link
            d3.select(this)
                .attr("stroke", OUTLINE_COLOR)
                .attr("stroke-width", 4);
        });
    
    const node = svg.append("g")
        .attr("class", "nodes")
        .selectAll("image")
        .data(data.nodes)
        .enter()
        .append("image")
        .attr("href", d => d.type === "Host" ? '/gui/static/images/server.png' : '/gui/static/images/switch.png')
        .attr("width", NODE_SIZE)
        .attr("height", NODE_SIZE)
        .attr("cursor", "pointer")
        .call(drag(simulation))
        .on("click", async function(event, d) {
            event.stopPropagation();

            deselectAll();

            console.log(d)

            // Highlight the clicked node
            outlineFilter.select("feFlood").attr("flood-color", OUTLINE_COLOR);
            d3.select(this)
                .attr("filter", "url(#outlineFilter)");
    
            await fetchMenuDetails(`/gui/menu/details/${d.type.toLowerCase()}/${d.id}`);
        }); 

    const label = svg.append("g")
        .attr("class", "labels")
        .selectAll("text")
        .data(data.nodes)
        .enter()
        .append("text")
        .attr("dy", -20)
        .attr("text-anchor", "middle")
        .text(d => d.name ? d.name : d.id);

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
    sliceList.addEventListener("click", async function (event) {
        let target = event.target;
        if (event.target.tagName === "SPAN") target = event.target.parentElement;
        const selectedSlice = slices[target.dataset.index];
        if (selectedSlice !== undefined) {
            deselectAll();

            target.classList.toggle("selected");
            highlightSlice(target, selectedSlice);

            await fetchMenuDetails(`/gui/menu/details/slice/${selectedSlice.id}`);
        }
    });
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

function increaseZoom(quantity = 0.2) { 
    if (ratio < 3) {
        ratio += quantity;
        document.getElementById("network-graph").style.transform = `scale(${ratio})`;
    }
}

function decreaseZoom(quantity = 0.2) {
    if (ratio > 0.5) { 
        ratio -= quantity;
        document.getElementById("network-graph").style.transform = `scale(${ratio})`;
    }
}

function resetZoom() {
    ratio = 1.25;
    document.getElementById("network-graph").style.transform = `scale(${ratio})`;
}

function saveLayout() {
    if (graph_data !== undefined) {
        const layout = graph_data.nodes.map(node => ({
            id: node.id,
            type: node.type,
            x: node.x,
            y: node.y
        }));
        const links = graph_data.links.map(link => ({
            id: link.id,
            source: link.source.id,
            target: link.target.id
        }));
        const layoutJSON = JSON.stringify({ nodes: layout, links });
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
async function fetchData(endpoint, method = 'GET', body = null, baseUrl = API_BASE_URL) {
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

        const response = await fetch(baseUrl + endpoint, options);
        if (!response.ok) {
            throw new Error(`Error: ${response.status} - ${response.statusText}`);
        }

        response_json = await response.json();
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
async function updateSlice(sliceId, sliceData) {
    return await fetchData('/slices/' + sliceId, 'PUT', sliceData);
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

/* ----------------------- Editable Forms ----------------------- */

function makeEditable(details_selector, onconfirm=undefined) {
    let details = document.querySelector(details_selector);
    if (!details) console.log("No details found");
    let btn = details.querySelector('.confirm-btn');
    if (!btn) console.log("No button found");
    let form = details.querySelector('.details-form');
    if (!form) console.log("No form found");
    if (btn) {
        btn.addEventListener('click', function() {
            if (btn.classList.contains('editing')) {
                // Collect updated parameters
                const updatedParams = {};
                form.querySelectorAll('.editable').forEach(input => {
                    input.setAttribute('readonly', true);
                    updatedParams[input.name] = input.value;
                });

                // Reset button state
                btn.textContent = btn.getAttribute('initial-text');
                btn.removeAttribute('initial-text');
                btn.classList.remove('editing');
                // btn.style.backgroundColor = ''; // Reset to default color

                // Remove cancel button
                const cancelButton = details.querySelector('.cancel-btn');
                if (cancelButton) {
                    cancelButton.remove();
                }
                
                if (onconfirm) {
                    onconfirm(updatedParams).then((result) => {
                        if (!result)
                            alert("Failed to save the data.");
                        else
                            window.location.reload();
                    });
                }
            } else {
                // Enable editing
                btn.setAttribute('initial-text', btn.textContent);
                form.querySelectorAll('input.editable').forEach(input => {
                    input.removeAttribute('readonly');
                    input.setAttribute('data-original-value', input.value);
                });

                // Change button state to confirm
                btn.textContent = 'Confirm';
                btn.classList.add('editing');
                // btn.style.backgroundColor = '#ffc107'; // Change to a warning color

                // Create and append cancel button
                const cancelButton = document.createElement('button');
                cancelButton.textContent = 'Cancel';
                cancelButton.className = 'cancel-btn btn btn-secondary ml-2';
                cancelButton.setAttribute('style', "width: 100%; margin: 5px 0 !important;")
                btn.insertAdjacentElement('afterend', cancelButton);

                cancelButton.addEventListener('click', function() {
                    // Reset form inputs
                    form.querySelectorAll('.editable').forEach(input => {
                        input.setAttribute('readonly', true);
                        input.value = input.getAttribute('data-original-value');
                        input.removeAttribute('data-original-value');
                    });

                    // Reset button state
                    btn.textContent = btn.getAttribute('initial-text');
                    btn.removeAttribute('initial-text');
                    btn.classList.remove('editing');
                    btn.style.backgroundColor = ''; // Reset to default color

                    // Remove cancel button
                    cancelButton.remove();
                });
            }
        });
    }
}