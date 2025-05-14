# liblk

![License](https://img.shields.io/github/license/R0rt1z2/liblk)
![GitHub Issues](https://img.shields.io/github/issues-raw/R0rt1z2/liblk?color=red)

`liblk` is a simple and tiny python library for manipulating LK (_Little Kernel_) images. It's flexible and has an easy-to-use API.
The library requires Python 3.8 or higher.

## Installation

```bash
sudo apt install python3-pip # If you don't have pip installed.
pip3 install --upgrade git+https://github.com/R0rt1z2/liblk
```

## Examples
The folder [examples](https://github.com/R0rt1z2/liblk/tree/master/examples) contains a set of examples that aim to show how to use the library and highlight its features.

## Quick Start
```python
from liblk import LkImage

# Load an LK image
lk_image = LkImage("path/to/lk.img")

# Iterate through the partitions
for name, partition in lk_image.partitions.items():
    print(f"Partition: {name}, Size: {len(partition.data)} bytes")

# Apply a binary patch
lk_image.apply_patch("30b583b002ab", "00207047")
```

## License
This project is licensed under the GPL-3.0 License - see the [LICENSE](https://github.com/R0rt1z2/liblk/tree/master/LICENSE) file for details.