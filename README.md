# Docksmith

A lightweight container runtime built from scratch that mimics core Docker functionalities such as layered image builds, caching, and isolated container execution.

---

## Overview

Docksmith is a CLI-based containerization tool designed to demonstrate how modern container systems work internally. It supports building images from a custom `Docksmithfile`, managing layers using content-addressed storage, and running containers in isolated environments.

---

## Features

- Layered image builds  
- Build caching with cache hit/miss  
- Filesystem isolation using chroot + namespaces  
- Content-addressed storage (SHA256 digests)  
- Runtime environment variable overrides (`-e`)  
- `inspect` command for image metadata  
- `history` command for layer-wise breakdown  

---

## Supported Instructions

Docksmithfile supports:
- `FROM`
- `WORKDIR`
- `COPY`
- `RUN`
- `ENV`
- `CMD`

---

## Project Structure
docksmith/
│
├── docksmith.py # CLI entry point
├── build_engine.py # Build system
├── runtime.py # Container execution
├── manifest.py # Image metadata handling
├── layer_store.py # Layer storage logic
├── cache_store.py # Build cache system
├── storage.py # Path + storage helpers
├── sample_app/ # Sample application
├── Docksmithfile # Build instructions


---

## Usage

### Build Image
python3 docksmith.py build -t myapp:latest .

### Run Container
python3 docksmith.py run myapp:latest
