import json

def get_organic_grid_js(grid_json, team_colors_json, team_strokes_json, team_meta_json, MT):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/d3-delaunay@6"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Share+Tech+Mono&display=swap');
        body {{ margin: 0; padding: 0; background-color: transparent; overflow: hidden; }}
        .voronoi-cell {{ stroke-width: 1.5px; transition: fill 0.3s, opacity 0.3s; cursor: crosshair; }}
        .voronoi-cell:hover {{ opacity: 0.8; stroke: #fff !important; stroke-width: 2.5px !important; z-index: 10; }}
        .amoeba-border {{ stroke: rgba(100,255,100,0.1); stroke-width: 1; fill: none; pointer-events: none; }}
        .map-wrap {{
            background: linear-gradient(135deg, #020d08 0%, #030f0a 40%, #020a06 100%);
            border: 1px solid rgba(100,255,100,0.15); border-radius: 6px;
            box-shadow: inset 0 0 60px rgba(0,0,0,0.6);
            position: relative; overflow: hidden;
            width: 100%; height: 500px;
        }}
        #d3-tooltip {{
            position: absolute; background: rgba(5, 10, 15, 0.95); border: 1px solid #D4AF37; border-radius: 4px;
            padding: 10px; color: #fff; font-family: 'Share Tech Mono', monospace; font-size: 12px;
            pointer-events: none; opacity: 0; transition: opacity 0.1s; z-index: 100; box-shadow: 0 0 15px rgba(0,0,0,0.8);
        }}
        .tt-title {{ font-family: 'Orbitron', monospace; color: #D4AF37; font-size: 14px; margin-bottom: 5px; border-bottom: 1px solid rgba(212,175,55,0.3); padding-bottom: 3px; }}
        .tt-row {{ display: flex; justify-content: space-between; width: 140px; margin-bottom: 2px; }}
        .tt-lbl {{ color: #888; }}
        .tt-val {{ color: #00E5FF; font-weight: 700; }}
    </style>
    </head>
    <body>
    <div class="map-wrap">
        <div id="d3-map" style="width: 100%; height: 100%; display: flex; justify-content: center; align-items: center;"></div>
        <div id="d3-tooltip"></div>
    </div>
    <script>
        const width = 600, height = 500;
        const svg = d3.select("#d3-map").append("svg")
            .attr("viewBox", `0 0 ${{width}} ${{height}}`)
            .attr("style", "width:100%; height:100%; display:block; padding: 10px;");
        
        const grid = {grid_json};
        const colors = {team_colors_json};
        const strokes = {team_strokes_json};
        const meta = {team_meta_json};
        const my_team = "{MT}";
        
        const n = grid.length;
        const phi = (1 + Math.sqrt(5)) / 2;
        const points = [];
        for (let i = 0; i < n; i++) {{
            const r = 180 * Math.sqrt((i + 0.5) / n);
            const theta = 2 * Math.PI * i / phi;
            const noiseX = Math.sin(i * 123) * 15;
            const noiseY = Math.cos(i * 321) * 15;
            points.append([width/2 + r*Math.cos(theta) + noiseX, height/2 + r*Math.sin(theta) + noiseY]);
        }}

        const delaunay = d3.Delaunay.from(points);
        const voronoi = delaunay.voronoi([0, 0, width, height]);

        const tooltip = d3.select("#d3-tooltip");

        svg.selectAll(".voronoi-cell")
            .data(points)
            .enter().append("path")
            .attr("class", "voronoi-cell")
            .attr("d", (d, i) => voronoi.renderCell(i))
            .attr("fill", (d, i) => {{
                const owner = grid[i];
                return owner ? colors[owner] : "#0a1a0e";
            }})
            .attr("stroke", (d, i) => {{
                const owner = grid[i];
                return owner ? strokes[owner] : "rgba(0,255,100,0.05)";
            }})
            .on("mouseover", function(event, d) {{
                const i = points.indexOf(d);
                const owner = grid[i];
                const tMeta = meta[owner] || {{ hp: 0, ap: 0, terr: 0, members: 0 }};
                
                tooltip.style("opacity", 1)
                    .html(`
                        <div class="tt-title">${{owner || "NEUTRAL ZONE"}}</div>
                        <div class="tt-row"><span class="tt-lbl">INDEX:</span><span class="tt-val">${{i}}</span></div>
                        ${{owner ? `
                            <div class="tt-row"><span class="tt-lbl">HP:</span><span class="tt-val">${{tMeta.hp}}</span></div>
                            <div class="tt-row"><span class="tt-lbl">AP:</span><span class="tt-val">${{tMeta.ap}}</span></div>
                        ` : '<div class="tt-row"><span class="tt-lbl">STATUS:</span><span class="tt-val">UNCLAIMED</span></div>'}}
                    `);
            }})
            .on("mousemove", function(event) {{
                tooltip.style("left", (event.layerX + 15) + "px")
                       .style("top", (event.layerY + 15) + "px");
            }})
            .on("mouseout", function() {{ tooltip.style("opacity", 0); }});

        // Add Amoeba Borders
        svg.append("path")
            .attr("class", "amoeba-border")
            .attr("d", voronoi.render());

    </script>
    </body>
    </html>
    """
