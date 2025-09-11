export const minMax = (points: number[]) => {
  return points.reduce(
    (acc, val) => {
      acc[0] = val < acc[0] ? val : acc[0];
      acc[1] = val > acc[1] ? val : acc[1];
      return acc;
    },
    [Infinity, -Infinity],
  );
};

export const getMiddlePoint = (points: number[][]) => {
  const x = points.reduce((acc, val) => acc + val[0], 0) / points.length;
  const y = points.reduce((acc, val) => acc + val[1], 0) / points.length;
  return { x, y };
};

// Note: this is only for filtering initialPolygons; we start from zero initialPolygons
export const isPolygonClosed = (points: number[][]) => {
  return points.length >= 3;
};

// https://stackoverflow.com/a/63638091/5403217
export const isInsidePoly = (mousePos, polygons) => {
  // ray-casting algorithm based on
  // https://wrfranklin.org/Research/Short_Notes/pnpoly.html
  
  let [x, y] = mousePos;
  for (let pi = 0; pi < polygons.length; pi++) {
    let points = polygons[pi];
    let inside = false;
    for (var i = 0, j = points.length - 1; i < points.length; j = i++) {
      var [xi, yi] = points[i];
      var [xj, yj] = points[j];
      var intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
      if (intersect) {
        inside = !inside;
      }
    }
    if (inside) {
      return true;
    }
  }
  return false;
};