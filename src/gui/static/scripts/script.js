const BASE_URL = `http://${CONTROLLER_IP}:${CONTROLLER_PORT}`;

/* ---------------------- Global variables ---------------------- */

const DISABLED_COLOR = "#dc3545";
const ENABLED_COLOR = "#28a745";
const OUTLINE_COLOR = "#FF6347";
const LINK_COLOR = "#aaa";
const NODE_SIZE = 35;

var graph_data = undefined;
var slices = [];
var ratio = 1.25;
var outlineFilter = undefined;


// Global variables to manage new slice creation
let isCreatingNewSlice = false;
let newSliceNodes = []; // stores selected node IDs
let newSliceIdCounter = 0;

/* ----------------------- Onload helper ----------------------- */

document.addEventListener("DOMContentLoaded", async () => {

    document.getElementById("network-graph").style.transform = `scale(${ratio})`;

    // Default data structure
    graph_data = {
        nodes: await getNodes(),
        links: await getLinks()
    };

    slices = await getSlices();

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
        sliceText.textContent = `${slice.name}`;
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
    if (isCreatingNewSlice) return;
    const menu = document.getElementById('details-menu');
    const target = document.getElementById('details-container');
    // add class
    if (menu.classList.contains('closed')) {
        menu.classList.remove('closed');
        menu.classList.add('opened');
        increaseZoom(0.4);
    }
    target.classList.remove('editing');

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
    if (!menu.classList.contains('opened')) return;
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
        .on("click", async function(event, d) {
            if (isCreatingNewSlice)
                return;
            event.stopPropagation();

            deselectAll();

            // Highlight the clicked link
            d3.select(this)
                .attr("stroke", OUTLINE_COLOR)
                .attr("stroke-width", 4);

            await fetchMenuDetails(`/gui/menu/details/link/${d.id}`);
        });
    
    const node = svg.append("g")
        .attr("class", "nodes")
        .selectAll("image")
        .data(data.nodes)
        .enter()
        .append("image")
        .attr("href", d => d.type === "Host" ? `${STATIC_FOLDER}/images/server.png` : `${STATIC_FOLDER}/images/switch.png`)
        .attr("width", NODE_SIZE)
        .attr("height", NODE_SIZE)
        .attr("cursor", "pointer")
        .call(drag(simulation))
        .on("click", async function(event, d) {
            if (isCreatingNewSlice)
                return;
            event.stopPropagation();

            deselectAll();

            // Highlight the clicked node
            outlineFilter.select("feFlood").attr("flood-color", OUTLINE_COLOR);
            d3.select(this)
                .attr("filter", "url(#outlineFilter)");
    
            if (d.type === "Host")
                path = `${GuiPaths.HOST_DETAILS.replace("{host_id}", d.id)}`;
            else if (d.type === "Switch")
                path = `${GuiPaths.SWITCH_DETAILS.replace("{switch_id}", d.id)}`;
            else {
                console.log("Unknown node type:", d.type);
                return;
            }
            await fetchMenuDetails(path);
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
        if (isCreatingNewSlice)
            return;
        let target = event.target;
        if (event.target.tagName === "SPAN") target = event.target.parentElement;
        const selectedSlice = slices[target.dataset.index];
        if (selectedSlice !== undefined) {
            deselectAll();

            target.classList.toggle("selected");
            highlightSlice(target, selectedSlice);

            await fetchMenuDetails(`${GuiPaths.SLICE_DETAILS.replace("{slice_id}", selectedSlice.id)}`);
        }
    });
}

/**
 * Animate a packet along a series of nodes using an image.
 * @param {Array} steps - An array of node IDs representing the path, e.g. ['h1', 's1', 's2', 'h2'].
 * @param {Number} duration - Duration (in ms) for each transition between nodes.
 */
function animatePacketPath(steps, duration = 800) {
    const svg = d3.select("#network-graph");

    const PACKET_SIZE = 40;

    // Create a packet image element
    const packet = svg.append("image")
        .attr("href", `${STATIC_FOLDER}/images/packet.png`)
        .attr("width", PACKET_SIZE)
        .attr("height", PACKET_SIZE)
        .attr("opacity", 1);

    // Helper: get node data by id
    function getNodeById(id) {
        return graph_data.nodes.find(node => node.id === id);
    }

    // Start at the first node in the path
    let startNode = getNodeById(steps[0]);
    if (!startNode) {
        console.error("Starting node not found:", steps[0]);
        return;
    }
    packet.attr("x", startNode.x - PACKET_SIZE / 2)
          .attr("y", startNode.y - PACKET_SIZE / 2);

    // Recursive function to animate packet through steps
    function moveToStep(index) {
        if (index >= steps.length) {
            packet.transition().duration(500).style("opacity", 0).remove();
            return;
        }
        let nextNode = getNodeById(steps[index]);
        if (!nextNode) {
            console.error("Node not found for step:", steps[index]);
            return;
        }
        packet.transition()
            .duration(duration)
            .attr("x", nextNode.x - PACKET_SIZE / 2)
            .attr("y", nextNode.y - PACKET_SIZE / 2)
            .on("end", () => moveToStep(index + 1));
    }

    // Begin the animation from the second step (index 1)
    moveToStep(1);
}



/* ----------------------- New Slice Management ----------------------- */

// Start new slice creation mode
async function startNewSlice() {
    await fetchMenuDetails(`${GuiPaths.NEW_SLICE_DETAILS}`);
    isCreatingNewSlice = true;
    
    newSliceNodes = [];
    deselectAll(); // Deselect any previous selection (and hide lateral menu)
    document.querySelector(".graph-info").innerText = "Select the nodes in the network to include in the new slice:";
    document.querySelector(".graph-info").classList.add("show");

    slice_lis = document.querySelectorAll("#slice-list li");
    for (let slice_li of slice_lis)
        slice_li.classList.add("disabled");

    new_slice_btn = document.getElementById("new-slice-btn");
    new_slice_btn.onclick = finalizeNewSlice;
    new_slice_btn.innerHTML = "Confirm New Slice <i class='bi bi-pencil-fill'></i>";

    cancel_slice_btn = document.getElementById("cancel-new-slice-btn");
    cancel_slice_btn.style.display = "inline-block";
    cancel_slice_btn.onclick = cancelNewSlice;

    // Override node click events to handle slice selection and disable lateral menu events
    d3.selectAll("image")
      .on("click.newSlice", function(event, d) {
         event.stopPropagation();
         event.stopImmediatePropagation(); // Prevent the lateral menu from appearing
         toggleNodeSelectionForNewSlice(d3.select(this), d);
      });

    // Also disable lateral menu events on links during new slice mode
    d3.selectAll("line")
      .on("click.newSlice", function(event, d) {
         event.stopPropagation();
         event.stopImmediatePropagation();
      });
}

// Toggle node selection for the new slice
function toggleNodeSelectionForNewSlice(nodeSelection, nodeData) {
    const nodeId = nodeData.id;
    if (newSliceNodes.includes(nodeId)) {
        newSliceNodes = newSliceNodes.filter(id => id !== nodeId);
    } else {
        newSliceNodes.push(nodeId);
    }
    
    // For visual feedback: compute the links connecting the currently selected nodes
    const computedLinks = graph_data.links.filter(link => {
        const sourceId = (typeof link.source === "object") ? link.source.id : link.source;
        const targetId = (typeof link.target === "object") ? link.target.id : link.target;
        return newSliceNodes.includes(sourceId) && newSliceNodes.includes(targetId);
    }).map(link => link.id);
    
    // Use your existing highlightSlice to highlight the selected nodes and their interconnecting links
    const tempSlice = { nodes: newSliceNodes, links: computedLinks };
    highlightSlice(null, tempSlice);
}

// Finalize new slice creation; the final slice object stores each node's id and type.
async function finalizeNewSlice() {
    if (!isCreatingNewSlice) return;
    
    // Build the final slice, including the type of each selected node
    const finalNodes = newSliceNodes.map(nodeId => {
        let nodeData = graph_data.nodes.find(n => n.id === nodeId);
        return { id: nodeId, type: nodeData ? nodeData.type : null };
    });

    // get all the nodes with `type == 'Host'` and add it to hosts array
    let hosts = [];
    let switches = [];
    for (let node of finalNodes) {
        if (node.type === 'Host')
            hosts.push(node.id);
        else if (node.type === 'Switch')
            switches.push(node.id);
    }

    // Check if at least one node is selected
    if (finalNodes.length < 2) {
        alert("Please select at least two nodes.");
        return;
    }
    
    const newSlice = {
        hosts: hosts,
        switches: switches,
    };

    // Fetch slice form data
    invalid = false;
    document.querySelector('.details-form').querySelectorAll('.editable').forEach(input => {
        if (invalid) return;
        if (input.value === "") {
            invalid = true;
            alert("Please fill all the fields.");
            return;
        }
        newSlice[input.name] = input.value;
    });
    if (invalid) return;
    const sliceRules = getDefinedSliceRules();
    if (!sliceRules) return;
    newSlice['rules'] = sliceRules;

    console.log("New slice:", newSlice);

    document.getElementById('request-indicator').classList.add('show');
    await fetchData(`${GuiPaths.SLICES}`, 'POST', newSlice);
    document.getElementById('request-indicator').classList.remove('show');
    
    // Reset new slice mode and remove temporary event listeners on nodes and links
    isCreatingNewSlice = false;
    newSliceNodes = [];
    d3.selectAll("image").on("click.newSlice", null);
    d3.selectAll("line").on("click.newSlice", null);

    window.location.reload();
}

// Update slice list UI based on the slices array.
function updateSliceListUI() {
    const sliceList = document.getElementById("slice-list");
    sliceList.innerHTML = "";
    slices.forEach((slice, index) => {
        const listItem = document.createElement("div");
        listItem.innerText = `Slice ${index + 1}: ${slice.nodes.length} node(s)`;
        listItem.dataset.index = index;
        listItem.classList.add("slice-item");
        sliceList.appendChild(listItem);
    });
}

// Cancel new slice creation
function cancelNewSlice() {
    if (!isCreatingNewSlice) return;

    closeDetailsMenu();

    deselectAll();

    // Reset new slice mode and remove temporary event listeners on nodes and links
    isCreatingNewSlice = false;
    newSliceNodes = [];
    d3.selectAll("image").on("click.newSlice", null);
    d3.selectAll("line").on("click.newSlice", null);

    slice_list_lis = document.querySelectorAll("#slice-list li");
    for (let slice_li of slice_list_lis)
        slice_li.classList.remove("disabled");

    cancel_slice_btn = document.getElementById("cancel-new-slice-btn");
    cancel_slice_btn.style.display = "none";

    new_slice_btn = document.getElementById("new-slice-btn");
    new_slice_btn.onclick = startNewSlice;
    new_slice_btn.innerHTML = "New Slice <i class='bi bi-plus-lg'></i>";

    document.querySelector(".graph-info").classList.remove("show");
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

// Generic function to fetch data from an endpoint
async function fetchData(endpoint, method = 'GET', body = null, baseUrl = BASE_URL) {
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
    return await fetchData(`${ApiPaths.SLICES}`);
}

// Create a new slice
async function createSlice(sliceData) {
    return await fetchData(`${ApiPaths.SLICES}`, 'POST', sliceData);
}

// Update a slice
async function updateSlice(sliceId, sliceData) {
    return await fetchData(`${ApiPaths.SLICE.replace("{slice_id}", sliceId)}`, 'PUT', sliceData);
}

// Delete a slice
async function deleteSlice(sliceId) {
    return await fetchData(`${ApiPaths.SLICES}`, 'DELETE', { id: sliceId });
}

// Fetch nodes
async function getNodes() {
    return await fetchData(`${ApiPaths.NODES}`);
}

// Fetch links
async function getLinks() {
    return await fetchData(`${ApiPaths.LINKS}`);
}

/* ----------------------- Editable Forms ----------------------- */

function makeEditable(details_selector, onconfirm=undefined, oncancel=undefined) {
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
                valid = true;
                form.querySelectorAll('.editable').forEach(input => {
                    if (input.value === "") {
                        valid = false;
                        alert("Please fill all the fields.");
                        return;
                    }
                    updatedParams[input.name] = input.value;
                });
                if (!valid) return;
                
                if (onconfirm) {
                    valid = onconfirm(updatedParams).then((result) => {
                        if (!result)
                            return;

                        form.querySelectorAll('.editable').forEach(input => {
                            input.setAttribute('readonly', true);
                        });

                        // Reset button state
                        btn.textContent = btn.getAttribute('initial-text');
                        btn.removeAttribute('initial-text');
                        btn.classList.remove('editing');
                        // remove editing class from closest parent with class details-container
                        btn.closest('.details-container').classList.remove('editing');

                        // Remove cancel button
                        const cancelButton = details.querySelector('.cancel-btn');
                        if (cancelButton) {
                            cancelButton.remove();
                        }

                        // Remove titles from delete buttons
                        details.querySelectorAll('.delete-list-item').forEach(deleteButton => {
                            deleteButton.removeAttribute('title');
                        });

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
                // add editing class to closest parent with class details-container
                btn.closest('.details-container').classList.add('editing');

                // Create and append cancel button
                const cancelButton = document.createElement('button');
                cancelButton.textContent = 'Cancel';
                cancelButton.className = 'cancel-btn btn btn-secondary ml-2';
                cancelButton.setAttribute('style', "width: 100%; margin: 5px 0 !important;")
                btn.insertAdjacentElement('afterend', cancelButton);

                // Add titles to delete buttons
                details.querySelectorAll('.delete-list-item').forEach(deleteButton => {
                    deleteButton.setAttribute('title', 'Remove');
                });

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
                    // remove editing class from closest parent with class details-container
                    btn.closest('.details-container').classList.remove('editing');

                    // Remove cancel button
                    cancelButton.remove();
                    
                    // Remove titles from delete buttons
                    details.querySelectorAll('.delete-list-item').forEach(deleteButton => {
                        deleteButton.removeAttribute('title');
                    });

                    if (oncancel) {
                        oncancel();
                    }
                });
            }
        });
    }
}
function getDefinedSliceRules() {
    rules = {};
    // fetch ports
    var portsList = document.querySelector('.ports-list');
    var ports = [];
    portsList.querySelectorAll('li').forEach(li => {
        ports.push(li.querySelector('span').innerText);
    });
    rules['allowed_ports'] = ports;
    // fetch protocols
    var protocolsList = document.querySelector('.protocols-list');
    var protocols = [];
    protocolsList.querySelectorAll('li').forEach(li => {
        protocols.push(li.querySelector('span').innerText);
    });
    rules['allowed_protocols'] = protocols;
    // fetch services
    var servicesList = document.querySelector('.services-list');
    var services = {};
    servicesList.querySelectorAll('li').forEach(li => {
        var ip = li.querySelector('mark').innerText;
        var ports = [];
        li.querySelectorAll('.badge').forEach(span => {
            ports.push(span.innerText);
        });
        services[ip] = ports;
    });
    rules['allowed_services'] = services;
    // check if at least a rule is defined
    if (Object.keys(services).length === 0 && protocols.length === 0 && ports.length === 0) {
        alert("At least one rule must be defined");
        return false;
    }
    return rules;
}
function restoreInitialSliceRules() {
    // restore protocols initial values
    var protocolsList = document.querySelector('.protocols-list');
    var initialProtocols = JSON.parse(protocolsList.getAttribute('initial-values'));
    protocolsList.innerHTML = '';
    for (var protocol of initialProtocols) {
        var newItem = document.createElement('li');
        newItem.classList.add('deletable');
        newItem.innerHTML = `
            <div class="d-flex align-items-center">
                <span class="badge bg-info" style="font-size: 1em;">${protocol}</span>
                <span class="delete-list-item" onclick="deleteRule(this.parentNode.parentNode)"><i class="bi bi-x"></i></span>
            </div>
        `;
        protocolsList.appendChild(newItem);
    }

    // restore ports initial values
    var portsList = document.querySelector('.ports-list');
    var initialPorts = JSON.parse(portsList.getAttribute('initial-values'));
    portsList.innerHTML = '';
    for (var port of initialPorts) {
        var newItem = document.createElement('li');
        newItem.classList.add('deletable');
        newItem.innerHTML = `
            <div class="d-flex align-items-center">
                <span class="badge bg-info" style="font-size: 1em;">${port}</span>
                <span class="delete-list-item" onclick="deleteRule(this.parentNode.parentNode)"><i class="bi bi-x"></i></span>
            </div>
        `;
        portsList.appendChild(newItem);
    }

    // restore services initial values
    var servicesList = document.querySelector('.services-list');
    var initialServices = JSON.parse(servicesList.getAttribute('initial-values'));
    servicesList.innerHTML = '';
    for (var ip in initialServices) {
        var ports = initialServices[ip];
        var newItem = document.createElement('li');
        newItem.classList.add('list-group-item', 'deletable', 'p-1');
        newItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-center ">
                <mark>${ip}</mark>
                <div>
                    ${ports.map(port => `<span class="badge bg-info">${port}</span>`).join('')}
                </div>
            </div>
            <div class="delete-list-item" onclick="deleteRule(this.parentNode)"><i class="bi bi-x"></i></div>
        `;
        servicesList.appendChild(newItem);
    }
}