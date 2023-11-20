import os
import argparse
from pathlib import Path
import shutil
import random

def main():
    r"""
    Utility script to move some train data (images and labels) into a different folder.
    """

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--source_dir",
        "-sd",
        type=str,
        default=None,
        help="source dir to move files from",
    )
    arg_parser.add_argument(
        "--dest_dir",
        "-dd",
        type=str,
        default=None,
        help="destination dir to move files to",
    )
    arg_parser.add_argument(
        "--num", "-n", type=int, default=None, help="number of files to move"
    )
    args = arg_parser.parse_args()

    img_paths = sorted(
        filter(lambda x: x.endswith(".png") or x.endswith(".jpg"), os.listdir(args.source_dir + "/images"))
    )[0 : args.num]

    print(img_paths)

    # randomly sample
    img_paths_shuffled = random.sample(img_paths, len(img_paths))

    label_paths = []

    for img_name in img_paths_shuffled:
        img_path = Path(args.source_dir + "/images") / img_name
        dest_path = Path(args.dest_dir + "/images") / img_name
        shutil.move(img_path, dest_path)
        # print(img_path)
        # print(dest_path)

        label_path = img_path.parents[1] / "labels" / img_name.replace('.png', '.txt').replace('.jpg', '.txt')
        label_paths.append(label_path)

    for label_path in label_paths:
        dest_path = Path(args.dest_dir + "/labels") / label_path.name
        shutil.move(label_path, dest_path)
        # print(label_path)
        # print(dest_path)


if __name__ == "__main__":
    main()
