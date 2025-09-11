// react hook that returns polygons data:

import { useCallback } from "react";
import { useDispatch, useSelector } from "react-redux";
import { createSelector } from "reselect";

import { RootState } from "../store/index.ts";
import { updatePolygonLabel, updatePolygonSize, deleteOne, deleteAll } from "../store/slices/polygonSlice.ts";

export const useGetPolygons = () => {
  const dispatch = useDispatch();
  const updateLabel = useCallback(
    (input: { id: string; label: string }) => dispatch(updatePolygonLabel(input)),
    [dispatch],
  );
  const updateSize = useCallback(
    (input: { id: string; size: string }) => dispatch(updatePolygonSize(input)),
    [dispatch],
  );
  const deletePolygons = useCallback((isFabric) => dispatch(deleteAll(isFabric)), [dispatch]);
  const deletePolygon = useCallback((input: { index: number; isFabric: boolean }) => dispatch(deleteOne(input)), [dispatch]);

  // Create a base selector that fetches the polygons array from the state
  const polygonsBaseSelector = (state) => state.polygon.present.polygons;
  
  // Create a memoized selector that transforms the polygons
  const polygonsSelector = createSelector(
    polygonsBaseSelector,
    (polygons) => polygons.map(polygon => ({
      id: polygon.id,
      label: polygon.label,
      points: polygon.points,
      flattenedPoints: polygon.points.reduce((a, b) => a.concat(b), []),
      isFabric: polygon.isFabric,
      size: polygon.size,
    }))
  );
  
  // Use the memoized selector in your component
  const polygons = useSelector(polygonsSelector);

  const activePolygonIndex = useSelector(
    (state: RootState) => state.polygon.present.activePolygonIndex,
  );

  return {
    polygons,
    activePolygonIndex,
    updateLabel,
    updateSize,
    deletePolygon,
    deletePolygons,
  };
};