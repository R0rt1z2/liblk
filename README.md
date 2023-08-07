# liblk

![License](https://img.shields.io/github/license/R0rt1z2/liblk)
![GitHub Issues](https://img.shields.io/github/issues-raw/R0rt1z2/liblk?color=red)

`liblk` is a simple and tiny python library for manipulating LK (_Little Kernel_) images. It's flexible and has an easy-to-use API.
The library requires Python 3.11 or higher.

## Installation

```bash
sudo apt install python3-pip # If you don't have pip installed.
pip3 install --upgrade git+https://github.com/R0rt1z2/liblk
```

## Examples
The folder [examples](https://github.com/R0rt1z2/liblk/tree/master/examples) contains a set of examples that aim to show how to use the library and highlight its features.

## Quick Start
The library is very simple to use. You can use it to dump the information of an LK image. For example, to get details of all the partitions in the LK image, you can use the following code:

```python
import sys
from liblk.LkImage import LkImage

def main():
    lk_image = LkImage(sys.argv[1])
    partitions = lk_image.get_partition_list()

    for partition in partitions:
        print(str(partition))

if __name__ == "__main__":
    main()
```

## License
This project is licensed under the GPL-3.0 License - see the [LICENSE](https://github.com/R0rt1z2/liblk/tree/master/LICENSE) file for details.