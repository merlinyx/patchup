import React from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import AnnotateApp from './pages/AnnotateApp.tsx';

// Change the path to the fabric scraps image you want to use
const scrapsSource = "./images/fabric_scraps.jpg";

const App = () => {
  return (
    <BrowserRouter>
      <div>
        <Routes>
          <Route path="/" element=
            {<AnnotateApp
              initialData={[]}
              scrapsSource={scrapsSource} />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
