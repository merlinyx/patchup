import { configureStore, combineReducers } from "@reduxjs/toolkit";
import undoable from "redux-undo";
import { v4 as uuidv4 } from "uuid";
import type { PolygonInputProps } from "../lib/types.ts";
import polygonReducer from "./slices/polygonSlice.ts";
import { isPolygonClosed } from "../utils/index.ts";

const rootReducer = combineReducers({
  polygon: undoable(polygonReducer, {
    filter: function filterActions(action: any) {
      if (action.type === "polygon/setPolygons" && action.payload?.shouldUpdateHistory !== undefined) {
        return action.payload.shouldUpdateHistory;
      }
      return false;
    },
  }),
});

export const initStore = (initialPolygons?: PolygonInputProps[]) => {
  const filteredPolygons = initialPolygons?.length
    ? initialPolygons
        .filter((polygon) => isPolygonClosed(polygon.points))
        .map((polygon, initialindex) => ({
          id: uuidv4(),
          index: initialindex,
          label: `Polygon-${initialindex + 1}`,
          isFinished: true,
          isFabric: false,
          flattenedPoints: polygon.points.reduce((a, b) => a.concat(b), []),
          ...polygon,
        }))
    : [];

  return configureStore({
    reducer: rootReducer,
    preloadedState: initialPolygons && {
      polygon: {
        past: [],
        present: {
          polygons: filteredPolygons,
          activePolygonIndex: filteredPolygons.length - 1,
        },
        future: [],
      },
    },
  });
};

export type RootState = ReturnType<typeof rootReducer>;
export type AppStore = ReturnType<typeof initStore>;
export type AppDispatch = AppStore["dispatch"];