import React from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import AnnotateApp from './pages/AnnotateApp.tsx';
import AssignApp from './pages/AssignApp.tsx';
import PlacingApp from './pages/PlacingApp.tsx';

// const imageSource = "./images/fish1.png";
// const scrapsSource = "./images/scraps5.jpg";
const imageSource = "./images/cube.png";
const scrapsSource = "./images/audrey/scrap7.jpg";

const App = () => {
  // const annotateWidth = window.innerWidth / 2;
  const annotateWidth = 400;

  return (
    <BrowserRouter>
      <div>
        <Routes>
          <Route path="/" element=
            {<AnnotateApp
              initialData1={[]}
              initialData2={[]}
              annotateWidth={annotateWidth}
              imageSource={imageSource}
              scrapsSource={scrapsSource} />} />
          <Route path="/assign" element=
            {<AssignApp
              imageSource={imageSource}
              scrapsSource={scrapsSource} />} />
          <Route path="/placing" element=
            {<PlacingApp 
              annotateWidth={annotateWidth}
              imageSource={imageSource}
              scrapsSource={scrapsSource} />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
