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

## Repository Structure

For each section there are one or more [Jupyter] Notebooks:

- ...

[Jupyter]: https://jupyter.org/