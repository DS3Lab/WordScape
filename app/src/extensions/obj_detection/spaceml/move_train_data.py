import os
import argparse
import shutil


def main():
    r"""
    Utility script to move some train data into a validation folder.
    """

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--train_dir",
        "-td",
        type=str,
        default=None,
        help="source train dir to move files from",
    )
    arg_parser.add_argument(
        "--val_dir",
        "-vd",
        type=str,
        default=None,
        help="destination val dir to move files to",
    )
    arg_parser.add_argument(
        "--num", "-n", type=int, default=None, help="number of files to move"
    )
    args = arg_parser.parse_args()

    meta_paths = []

    tar_paths = sorted(
        filter(lambda x: x.endswith(".tar"), os.listdir(args.train_dir + "/multimodal"))
    )[0 : args.num]

    for tar_name in tar_paths:
        tar_path = os.path.join(args.train_dir + "/multimodal", tar_name)
        meta_path = (
            "doc_meta_" + tar_name.replace("docs_", "").replace(".tar", "") + ".jsonl"
        )
        meta_paths.append(meta_path)

        shutil.move(tar_path, args.val_dir + "/multimodal")

    for meta_name in meta_paths:
        meta_path_inner = os.path.join(args.train_dir + "/meta", meta_name)
        shutil.move(meta_path_inner, args.val_dir + "/meta")


if __name__ == "__main__":
    main()
