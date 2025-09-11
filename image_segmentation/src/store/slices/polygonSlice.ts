import { PayloadAction, createSlice } from "@reduxjs/toolkit";
import { Polygon } from "../../lib/types.ts";
import { v4 as uuidv4 } from "uuid";

export interface PolygonAnnotationState {
  polygons: Polygon[];
  activePolygonIndex: number;
  shouldUpdateHistory?: boolean;
}

const initializeState = (isFabricInit: boolean): PolygonAnnotationState => ({
  polygons: [
    {
      id: uuidv4(),
      index: 0,
      points: [],
      flattenedPoints: [],
      isFinished: false,
      isFabric: isFabricInit,
      label: "Polygon 1",
      size: "",
    },
  ],
  activePolygonIndex: 0,
  shouldUpdateHistory: false,
});

export const polygonSlice = createSlice({
  name: "polygon",
  initialState: initializeState(false),
  reducers: {
    setPolygons: (
      state,
      action: PayloadAction<{
        polygons: PolygonAnnotationState["polygons"];
        shouldUpdateHistory?: boolean;
      }>,
    ) => {
      const { polygons, shouldUpdateHistory = true } = action.payload;
      state.polygons = polygons;
      state.shouldUpdateHistory = shouldUpdateHistory;
    },
    setActivePolygonIndex: (state, action) => {
      state.activePolygonIndex = action.payload;
    },
    updatePolygonLabel: (
      state,
      action: PayloadAction<{ id: Polygon["id"]; label: Polygon["label"] }>,
    ) => {
      const { id, label } = action.payload;
      const activePoly = state.polygons.find((p) => p.id === id);
      if (!activePoly) return;
      activePoly.label = label;
    },
    updatePolygonSize: (
      state,
      action: PayloadAction<{ id: Polygon["id"]; size: Polygon["size"] }>,
    ) => {
      const { id, size } = action.payload;
      const activePoly = state.polygons.find((p) => p.id === id);
      if (!activePoly) return;
      activePoly.size = size;
    },
    deleteAll: (state, action: PayloadAction<boolean>) => {
      const isFabric = action.payload;
      state.polygons = initializeState(isFabric).polygons;
      state.activePolygonIndex = 0;
      state.shouldUpdateHistory = false;
    },
    deleteOne: (state, action: PayloadAction< {index: number, isFabric: boolean} >) => {
      const { isFabric, index } = action.payload;
      if (state.polygons.length === 1) {
        state.polygons = initializeState(isFabric).polygons;
        state.activePolygonIndex = 0;
        state.shouldUpdateHistory = false;
        return;
      }
      state.polygons.splice(index, 1);
      for (let i = index; i < state.polygons.length; i++) {
        if (state.polygons[i].label === `Polygon-${i + 2}`) {
          state.polygons[i].label = `Polygon-${i + 1}`;
        }
      }
      state.activePolygonIndex = state.polygons.length + 1;
      state.shouldUpdateHistory = true;
    },
  },
});

export const { setPolygons, setActivePolygonIndex, updatePolygonLabel, updatePolygonSize, deleteOne, deleteAll } =
  polygonSlice.actions;

export default polygonSlice.reducer;