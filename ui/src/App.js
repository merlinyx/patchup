import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
// UseNavigate

import BinningPage from './lib/binning';
import PackingPage from './lib/packing';
import RectpackPage from './lib/rectpack';

import "./App.css";

const App = () => {
  return (
    <Router>
      <div className="App">
        <header className="App-header">
          <h3>PatchUp! - Upcycle Your Scraps</h3>
        </header>
        <Routes>
          <Route path="/" element={<BinningPage />} />
          <Route path="/packing" element={<PackingPage />} />
          <Route path="/rectpack" element={<RectpackPage />} />
        </Routes>
      </div>
    </Router>
  );
};

export default App;
