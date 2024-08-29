Leaner and Faster: The Web and DNS Can Benefit from CBOR
========================================================

This repository contains code and documentation to reproduce the experimental results and plots as well as the raw data results of the paper "[Leaner and Faster: The Web and DNS Can Benefit from CBOR](https://tbd)" published in TBD.

- TBD

**Abstract:**

> Decreasing latency in the World Wide Web (WWW) can significantly
> improve user experience and is now established as a key objective of
> the evolution of the Web, with major improvements achieved on the protocol
> layers.
> Nevertheless, the size of transferred objects continues to increase,
> countering those improvements.
> In this paper, we propose addressing this trend by employing
> components engineered for the constrained Internet of Things (IoT).
> We show that simply switching from data representation in JSON to
> the Concise Binary Object Representation (CBOR) offers a median gain
> of $14.4\%$ for a corpus of JSON objects collected on
> GitHub.
> A new CBOR-based DNS message format designed for use with DNS over
> HTTPS (DoH) and DNS over CoAP (DoC) provides mean byte savings of
> $64.0 \pm 50.0$ bytes in its packed form and shows large
> potential for additionally compressing names and addresses.
> We propose two name compression schemes that apply to the new CBOR
> format and save up to $116$ bytes in a response that
> cannot elide the question section.
> The decoder for our name compression
> scheme is lean and can fit into as little as $314$ bytes of binary build size.

## Requirements

First, clone this repository:

```sh
git clone https://tbd cbor-dns-eval-tbd
cd cbor-dns-eval-tbd
```

Then you have the choice between a [vagrant]-based set-up using a VM, or you can run [Jupyter] Lab natively on your system.

### Vagrant-based VM set-up

We provide a [vagrant] set-up in this repository. To use this, please [install vagrant] first,
according to the instructions for your operating system, including the [VirtualBox provider]. 
On Debian-based systems, such as Ubuntu, this can be done using the following command:

```sh
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt update && sudo apt install vagrant
sudo apt install virtualbox
```

It is highly recommended to update memory and CPU in line with your host machine (as much processing
power and RAM needed as possible) in the provider section of the [Vagrantfile]\ (search for
`v.memory` and `v.cpus` in the file). E.g., for 16GB RAM and 16 CPU cores, use the following.

```ruby
v.memory = 16384
v.cpus = 16
```

To start the VM, run the following.

```sh
vagrant up
vagrant reload
```

After finishing, go to the [Jupyter] Lab at http://localhost:8888/lab/tree/start.ipynb.

If port 8888 is already occupied on your host machine, change the value for `host:` of the
`config.vm.network "forward_port"` option in the [Vagrantfile], e.g. for port 8080 set the
following.

```ruby
config.vm.network "forwarded_port", guest: 8888, host: 8080
```

The Jupyter Lab will then be available at http://localhost:8080/lab/tree/start.ipynb.

### Native set-up

If you do not want to or cannot use a VM, please use this set-up.

Our [Jupyter] Notebooks were tested with Python 3.12.5.
We tested our setup on Ubuntu 22.04 and 24.04, but for generalized setup, please use [pyenv]
to set-up Python 3.12.5:

```sh
./pyenv-setup.sh
. ${HOME}/.bashrc
```

You will also need [bash], [curl], [npm], [GNU parallel], [pigz], [tshark], and a LaTeX distribution
[supported by Jupyter-TikZ] as well as [Poppler]'s `pdftocairo` tool. Please check the
installation instructions of each tool for your operating system.

All Python dependencies are listed in the [requirements.txt].

You can start [Jupyter] Lab as follows:

```sh
pyenv activate cbor-dns-eval-tbd
jupyter lab
```

The Jupyter Lab will then be available at http://localhost:8888/lab/tree/start.ipynb.

## Repository Structure

For each section there are one or more [Jupyter] Notebooks and a corresponding directory:

- Introduction: [01_introduction](./01_introduction.ipynb)
- Background and Related Work: [02_background](./02_background.ipynb)
- Evaluating the Use of CBOR for Object Encoding: [03_json2cbor_eval](./03_json2cbor_eval)

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
