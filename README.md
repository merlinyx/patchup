# PatchUp: Interactive Patchwork Design for Scrap Fabric Upcycling

We propose PatchUp, an interactive design tool for upcycling fabric scraps by packing them in an aesthetic way guided by traditional quilt block designs. The newly made fabrics from the scraps can be used for other crafting projects.

UI Walkthrough Video:
<iframe width="560" height="315" src="https://www.youtube.com/embed/RmI8TaRvA5Q?si=7sK3kPKaGF__vpwm" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

Implementation accompanying
```bibtex
@inproceedings{10.1145/3745778.3766667,
  address = {New York, NY, USA},
  series = {{SCF} '25},
  title = {PatchUp: Interactive Patchwork Design for Scrap Fabric Upcycling},
  isbn = {9798400720345},
  shorttitle = {PatchUp},
  doi = {10.1145/3745778.3766667},
  booktitle = {Proceedings of the 10th ACM Symposium on Computational Fabrication},
  publisher = {Association for Computing Machinery},
  author = {Mei, Yuxuan and Que, Lirong and Leake, Mackenzie and Schulz, Adriana},
  month = nov,
  year = {2025},
  pages = {1--17},
}
```
To cite this work, please use the BibTeX entry above.

## Repo setup

`conda create -n <newenv> python=3.11`
(It's not necessary to specify the python version)

`conda activate <newenv>`

`pip install colormath dill flask flask-cors gurobipy matplotlib numpy opencv-python pillow rectpack scikit-image scikit-learn seaborn` (if you run into additional packages missing from here please submit an issue and let me know!)

### Data Download

Please download the additional fabric data from the Google Drive [link](https://drive.google.com/file/d/16om-5sy1PsLroW6Lb9H_VzWNCMgdTtts/view?usp=sharing) and unzip under `fabric_data`.

### Gurobi Setup

`export GRB_LICENSE_FILE=<path to gurobi.lic>`

You need a Gurobi license to use the Gurobi solver and for academic purposes you can request a free academic license [here](https://www.gurobi.com/academia/academic-program-and-licenses/).

### Running the app

`cd <folder-name>`
(right now folder-name could be either image_segmentation or ui)

`npm install`

`conda activate <newenv>`

`npm run start-api`

`npm run start`

- image_segmentation: manual extraction of fabric images, or use the linked [netlify app](https://patchup-fabric-segmenter.netlify.app/) that uses SAM-based segmentation that's easier to work with. `fabric_data/example_scraps` shows an example of preprocessing done with the zip downloaded from the netlify app. The [repo](https://github.com/merlinyx/fabric_segmenter) here contains example photos under `public/images`. The preprocessing script is under `src/imgseg/compute_inner_images.ipynb`.

- ui: the main ui for PatchUp. See the above video walkthrough for how to use it or refer to the paper.

### ngrok Setup

The app sometimes is unstable due to the request-response loop sometimes racing (not actually sure the reason and couldn't figure out how to solve it) but we found that deploying over to ngrok dev domain and access it over that url solves the issue.

To use ngrok: sign up for an account and follow the Setup & Installation instructions on the [dashboard](https://dashboard.ngrok.com/). Then deploy using

`ngrok http 3000`

to access it at your custom ngrok dev domain. This service is free.

## Other Notes

Baselines repos are not included yet and if requested I'll find some other time to add the entire eval code.
