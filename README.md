Artifacts of “Leaner and Faster: The Web and DNS Can Benefit from CBOR”
=======================================================================

[![DOI][software-badge]][software-doi]
[![Datasets][data-badge]][data-doi]
[![Paper on IEEE Xplore][paper-badge]][paper-doi]

This repository contains code and documentation to reproduce the experimental results and plots of the paper "[Leaner and Faster: The Web and DNS Can Benefit from CBOR][paper-doi]" accepted at IEEE Transactions on Network and Service Management (IEEE TNSM).

- M. S. Lenders, C. Bormann, T. C. Schmidt, and M. Wählisch, “**Leaner and Faster: The Web and DNS Can Benefit from CBOR**,” IEEE Transactions on Network and Service Management (TNSM), vol. TBD, no. TBD, pp. TBD–TBD, TBD. 2026. https://doi.org/10.1109/TNSM.2026.TBD

**Abstract:**

> The Internet community has taken major efforts to decrease latency on the World Wide Web with significant improvements in accelerating content transport and in compressing static content.
> Less attention, however, has been dedicated to compression of dynamic content.
> Such content is commonly provided by JSON and DNS over HTTPS.
> Dynamic content objects continue to grow in size, which increases latency and fosters the digital inequality.
> In this paper, we propose to mitigate this increase by utilizing Concise Binary Object Representation (CBOR), a standard originally designed for the constrained Internet of Things (IoT) to restrict packet sizes and enable efficient encoding of data objects.
> We provide protocol design and three new data sets for the evaluation of dynamic content, DNS, and the loading of websites.
> Our key findings are the following:
> _(i)_ Switching the data representation from JSON to CBOR reduces data by up to 80%.
> This size reduction can decrease loading times by up to 13.8% when downloading large objects—even in local setups.
> _(ii)_ Enabling CBOR for DNS over HTTPS (DoH) and DNS over CoAP (DoC) reduces packet sizes significantly.
> Compressing only names combined with unpacked CBOR achieves maximum gain of 52.2%, using more complex but still lightweight Packed CBOR allows minimizing packets by up to 95.5%.
> Our lean decoder for name compression can fit into as little as 314 bytes of build size.
> Our results clearly show the potential of CBOR outside of IoT scenarios.
> Parts of this research have already influenced work within the IETF.


## Requirements

First, clone this repository:

```sh
git clone https://github.com/netd-tud/artifacts-tnsm26-cbor-dns-eval.git
cd artifacts-tnsm26-cbor-dns-eval
```

Or download the `artifacts-tnsm26-cbor-dns-eval-v0.9.1.zip` ZIP archive from [Zenodo][software-doi] and unzip it in the git repository.

For most sections there are one or more Jupyter notebooks containing documentation and the code to create the output we describe in that section. The number `XX` indicates which section it belongs to. Some of these notebooks have a corresponding directory which contain further code.

- **I. Introduction**, see [`01_introduction.ipynb`](./01_introductionn.ipynb).
- **II. Background and Related Work**, see [`02_background.ipynb`](./02_background.ipynb).
- **III. Evaluating the Use of CBOR for Object Encoding**, see [`03_json2cbor_eval.ipynb`](./03_json2cbor_eval.ipynb).
  + **Dataset Collection**, see [`03_json2cbor_eval/01_dataset_collection.ipynb`](03_json2cbor_eval/01_dataset_collection.ipynb)
  + **Request/Response Times**, see [`03_json2cbor_eval/02_request_response_time.ipynb`](03_json2cbor_eval/02_request_response_time.ipynb) (also used for Figure 2 in Introduction)
- **IV. Evaluating CBOR as DNS Message Format**, see [`04_cbor4dns_eval.ipynb`](./04_cbor4dns_eval.ipynb).
  + **Dataset Collection**, see [`04_cbor4dns_eval/01_dataset_collection.ipynb`](004_cbor4dns_eval/01_dataset_collection.ipynb)
  + **Encode to `application/dns+cbor`**, see [`04_cbor4dns_eval/02_encoding.ipynb`](04_cbor4dns_eval/02_encoding.ipynb)
  + **Prepararations for Common IP Prefixes and Name Suffixes Analysis**, see [`04_cbor4dns_eval/03_comp_pot_prep.ipynb`](04_cbor4dns_eval/03_comp_pot_prep.ipynb)
- **V. Evaluating the Name Compressors**, see [`05_implementation.ipynb`](./05_implementation.ipynb).
- **VI. End-to-end Validation**, see [`06_e2e_eval.ipynb`](./06_e2e_eval.ipynb).
- **VII. Discussion**, does not have any code.
- **VIII. Conclusion**, does not have any code.
- **Appendices**, do not have any code.

The required datasets we provide on [OPARA][data-doi], an open access data repository and archive provided by TU Dresden.

To run the Jupyter notebooks, you can either run them in a [Docker container](#dockerized-usage) (recommended usage) or natively on your host system [using UV](#using-uv).

### Dockerized Usage

This repository can be used using [`docker compose`](https://docs.docker.com/compose/install/). If you do not have root access to your machine, consider running in a virtual machine, otherwise, see ["Using UV"](#Using-UV) below. Once `docker compose` is installed, run `docker compose up` from a command-line in the directory you stepped into with the `cd` command above.

``` bash
docker compose up
```

Once it is done building the image, Jupyter Lab will start and a URL to open in your browser will be shown, e.g.,

```
jupyter-1  |     To access the server, open this file in a browser:
jupyter-1  |         file:/home/user/.local/share/jupyter/runtime/jpserver-12-open.html
jupyter-1  |     Or copy and paste one of these URLs:
jupyter-1  |         http://localhost:8888/lab?token=f63eeb3d8158079dfea465051cbb4598fbe5575f96a7ffdb
jupyter-1  |         http://127.0.0.1:8888/lab?token=f63eeb3d8158079dfea465051cbb4598fbe5575f96a7ffdb
```

If port `8888` is already in use on your system, you can also pick another using the `JUPYTER_PORT` environment variable:

```bash
JUPYTER_PORT=8889 docker compose up
```

If your host user has a different UID or GID than 1000, this also can be configured:

```bash
HOST_UID="$(id -u)" HOST_GID="$(id -g)" docker compose up
```

Now go to the Jupyter Lab at http://localhost:8888/lab/tree/00_start.ipynb (the port of the URL might differ if you changed it using `JUPYTER_PORT`).

#### Download from Other Container Registry

We provide the docker images needed for the artifacts at several container registries. You can find the image names for each repository in the following table.

| Image           | Docker Hub      |GitHub Packages  |Codeberg Packages|
|-----------------|-----------------|-----------------|-----------------|
|[Main](./Dockerfile)|[`docker.io/miri64/tnsm26-cbor-jupyter`](https://hub.docker.com/r/miri64/tnsm26-cbor-jupyter)|[`ghcr.io/miri64/tnsm26-cbor-jupyter`](https://github.com/users/miri64/packages/container/package/tnsm26-cbor-jupyter)|[`codeberg.org/miri64/tnsm26-cbor-jupyter`](https://codeberg.org/miri64/-/packages/container/tnsm26-cbor-jupyter)|
|[E2E Validation Lighthouse](./06_e2e_eval/Dockerfile.lighthouse)|[`docker.io/miri64/tnsm26-cbor-lighthouse`](https://hub.docker.com/r/miri64/tnsm26-cbor-lighthouse)|[`ghcr.io/miri64/tnsm26-cbor-lighthouse`](https://github.com/users/miri64/packages/container/package/tnsm26-cbor-lighthouse)|[`codeberg.org/miri64/tnsm26-cbor-lighthouse`](https://codeberg.org/miri64/-/packages/container/tnsm26-cbor-lighthouse)|
|[E2E Validation Proxies](./06_e2e_eval/Dockerfile.mitmproxy)|[`docker.io/miri64/tnsm26-cbor-proxy`](https://hub.docker.com/r/miri64/tnsm26-cbor-proxy)|[`ghcr.io/miri64/tnsm26-cbor-proxy`](https://github.com/users/miri64/packages/container/package/tnsm26-cbor-proxy)|[`codeberg.org/miri64/tnsm26-cbor-proxy`](https://codeberg.org/miri64/-/packages/container/tnsm26-cbor-proxy)|

Sadly, support to configure these easily is not provided when running `docker compose`. As such, the easiest way to use the repositories is to search and replace the `image:` key within the docker compose files. E.g., to use the Codeberg Packages registry, use the following

```sh
find . -name *.yaml | xargs grep -l 'image: *docker\.io/miri64' | xargs sed -i 's#image: *docker\.io/miri64#image: codeberg.org/miri64'
```

### Using UV

**We do not recommend this method**, since updates during the years since we published this repository might lead to incompatibilities.
However, you might need to use it, if you do not have access to Docker or a virtual machine where you can run Docker on your machine.

First, install the package and project manager for Python [UV](https://docs.astral.sh/uv/) (you might need to use flags like `--user` or `--system` to install this on your specific system, see [`pip` documentation](https://pip.pypa.io/en/stable/cli/pip_install/)):

```bash
pip install uv
```

UV has some advantages over the classic `pip` package manager: First, it is much faster. Second, it allows for a hassle-free deployment of python versions that are not pre-installed on your system.

Our Jupyter Notebooks were tested with Python 3.12 on a Debian 13 (Trixie) machine. As such, we recommend installing that Python version.

```bash
uv python install cpython-3.12
```

Additional dependencies from the system might be needed. Please have a look at the `apt-get install` (the Debian package manager command used to install dependencies there) line from our [Dockerfile](./Dockerfile) for a (Debian-13-based) listing of the dependencies.

Now create and step into a virtual environment for this repository.

```bash
uv venv --python python3.12 .env
. .env/bin/activate
```

Last, install the Python dependencies:

```bash
uv pip install -r requirements.txt
```

You now can start Jupyter Lab by running the following command (you might want to use the `--port` argument to change the port).

```bash
jupyter lab
```

Now go to the Jupyter Lab at http://localhost:8888/lab/tree/00_start.ipynb (the port of the URL might differ if you changed it using `--port`).

The directory `utils` contains additional helper functions and tools, such as our extended taxonomy tool for CBOR classification.

[paper-badge]: https://img.shields.io/badge/Paper-IEEE%20Xplore-green
[paper-doi]: https://doi.org/10.1109/TNSM.2026.TBD
[data-badge]: https://img.shields.io/badge/Data-OPARA-007f33
[data-doi]: https://doi.org/10.25532/OPARA-1530
[software-badge]: https://zenodo.org/badge/DOI/10.5281/zenodo.21790597.svg
[software-doi]: https://doi.org/10.5281/zenodo.21790597
