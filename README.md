Leaner and Faster: The Web and DNS Can Benefit from CBOR
========================================================

This repository contains code and documentation to reproduce the experimental results and plots as well as the raw data results of the paper "[Leaner and Faster: The Web and DNS Can Benefit from CBOR](https://tbd)" published in TBD.

- TBD

**Abstract:**

> The Internet community has taken major efforts to decrease latency in the World Wide Web with significant improvements in accelerating content transport and in compressing static content.
> Less attention, however, has been dedicated to dynamic content compression.
> Such content is commonly provided by JSON and DNS over HTTPS.
> Dynamic content objects continue to grow in size, which increases latency and fosters the digital inequality.
> Concise Binary Object Representation (CBOR) was originally introduced to restrict packet sizes in constrained Internet of Things (IoT) and enables efficient encoding of data objects.
> When switching the data representation from JSON to CBOR a corpus of JSON objects collected via the HTTP Archive reduces data by up to 80.0%.
> This size reduction can decrease loading times by up to 13.8% when downloading large objects—even in local setups.
> A new CBOR-based DNS message format designed for use with DNS over HTTPS (DoH) and DNS over CoAP (DoC) minimizes packets by up to 95.5% in its packed form and shows large potential for additionally compressing names and addresses.
> We contribute two name compression schemes that apply to the new CBOR format and save up to 226 bytes in a response.
> A lean decoder for these schemes can fit into as little as 314 bytes of build size.
> Further optimization proposals directly influenced our work on the new DNS message format within the IETF.

## Requirements

First, clone this repository:

```sh
git clone https://tbd cbor-dns-eval-tbd
cd cbor-dns-eval-tbd
```

Then you have the choice between a [vagrant]-based set-up using a VM, or you can run [Jupyter] Lab natively on your system.

## Dockerized Usage

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

Now go to the [Jupyter] Lab at http://localhost:8888/lab/tree/start.ipynb (the port of the URL might differ if you changed it using `JUPYTER_PORT`).

## Using UV

**We do not recommend this method**, since updates during the years since we published this repository might lead to incompatibilities.
However, you might need to use it, if you do not have access to Docker or a virtual machine where you can run Docker on your machine.

First, install the package and project manager for Python [UV](https://docs.astral.sh/uv/) (you might need to use flags like `--user` or `--system` to install this on your specific system, see [`pip` documentation](https://pip.pypa.io/en/stable/cli/pip_install/)):

```bash
pip install uv
```

UV has some advantages over the classic `pip` package manager: First, it is much faster. Second, it allows for a hassle-free deployment of python versions that are not pre-installed on your system.

Our [Jupyter] Notebooks were tested with Python 3.12 on a Debian 13 (Trixie) machine. As such, we recommend installing that Python version.

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

Now go to the [Jupyter] Lab at http://localhost:8888/lab/tree/start.ipynb (the port of the URL might differ if you changed it using `JUPYTER_PORT`).

## Repository Structure

Roughly, for each section there are one or more [Jupyter] Notebooks and a corresponding directory:

1. Introduction: [`01_introduction`](./01_introduction.ipynb)
2. Background and Related Work: [`02_background`](./02_background.ipynb)
3. Evaluating the Use of CBOR for Object Encoding: [`03_json2cbor_eval`](./03_json2cbor_eval.ipynb)
4. Evaluating CBOR as DNS Message Format: [`04_cbor4dns_eval`](./04_cbor4dns_eval.ipynb)
5. Evaluating the Name Compressors: [`05_implementation`](./05_implementation.ipynb)
6. Discussion: [`06_discussion`](./06_discussion.ipynb)
7. Conclusion: [`07_conclusion`](./07_conclusion.ipynb)
8. Appendices: [`0A_appendix`](./0A_appendix.ipynb)

The directory `utils` contains additional helper functions and tools, such as our extended taxonomy tool for CBOR classification.

[vagrant]: https://developer.hashicorp.com/vagrant
[install vagrant]: https://developer.hashicorp.com/vagrant/install
[VirtualBox provider]: https://developer.hashicorp.com/vagrant/docs/providers/virtualbox
[Vagrantfile]: ./Vagrantfile
[Jupyter]: https://jupyter.org/
[pyenv]: https://github.com/pyenv/pyenv
[bash]: https://www.gnu.org/software/bash/
[curl]: https://curl.se/
[npm]: https://www.npmjs.com/
[GNU parallel]: https://www.gnu.org/software/parallel/
[pigz]: https://zlib.net/pigz/
[tshark]: https://tshark.dev/
[supported by Jupyter-TikZ]: https://jupyter-tikz.readthedocs.io/stable/installation/#latex
[Poppler]: https://poppler.freedesktop.org/
[requirements.txt]: ./requirements.txt
