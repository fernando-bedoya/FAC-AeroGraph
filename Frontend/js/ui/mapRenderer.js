/**
 * Map Renderer - Responsabilidad única: Renderizar elementos gráficos en el mapa SVG (D3)
 */
class MapRenderer {
  drawRoute(route, airports, svg) {
    const origin = airports[route.u];
    const destination = airports[route.v];

    if (!origin || !destination) return;

    svg.append('path')
        .attr('id', `route-path-${origin.id}-${destination.id}`)
        .attr('d', `M${origin.x},${origin.y}L${destination.x},${destination.y}`)
        .attr('stroke', '#999')
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '5, 5')
        .attr('fill', 'none');
  }

  highlightRoute(segments, airports, svg) {
    svg.selectAll('.highlighted-route').remove();

    segments.forEach(segment => {
        const origin = airports[segment.origin];
        const destination = airports[segment.destination];

        if (!origin || !destination) return;

        svg.append('path')
            .attr('class', 'highlighted-route')
            .attr('id', `route-path-${origin.id}-${destination.id}`)
            .attr('d', `M${origin.x},${origin.y}L${destination.x},${destination.y}`)
            .attr('stroke', 'dodgerblue')
            .attr('stroke-width', 3)
            .attr('fill', 'none');
    });
  }
}

export const mapRenderer = new MapRenderer();