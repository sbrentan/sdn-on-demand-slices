document.addEventListener("DOMContentLoaded", () => {
    // Default data structure
    const defaultData = {
        nodes: [
            { id: "h1", type: "host" },
            { id: "h2", type: "host" },
            { id: "s1", type: "switch" },
            { id: "s2", type: "switch" },
            { id: "s3", type: "switch" },
            { id: "s4", type: "switch" },
        ],
        links: [
            { source: "h1", target: "s1" },
            { source: "h2", target: "s2" },
            { source: "s1", target: "s2" },
            { source: "h1", target: "s3" },
            { source: "s3", target: "s4" },
            { source: "s4", target: "h2" },
        ],
    };

    // Retrieve saved layout from cookie
    const savedLayout = getCookie("networkLayout");
    const data = savedLayout ? JSON.parse(savedLayout) : defaultData;

    const width = document.getElementById("network-graph").clientWidth;
    const height = 600;

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
        .attr("fill", d => d.type === "host" ? "blue" : "green")
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

    // Save layout button event
    document.getElementById("save-layout").addEventListener("click", () => {
        const layout = data.nodes.map(node => ({
            id: node.id,
            type: node.type,
            x: node.x,
            y: node.y
        }));
        const layoutJSON = JSON.stringify(layout);
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
