from ultralytics import YOLO
import argparse
import os


def main():
    r"""
    A script to run a YOLO-Wordscript experiment. Arguments are the path to the YOLO dataset yaml, and the GPUs to use.
    """
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--config_path",
        "-cp",
        type=str,
        default="/home/valde/GitHub/msc-thesis/data/experiments/baseline/dataset.yaml",
        help="path to config",
    )
    arg_parser.add_argument(
        "--gpu_usage",
        "-gu",
        type=str,
        default="0,1,2,3",
        help="Comma separated list of CUDA GPU IDs",
    )
    arg_parser.add_argument(
        "--epochs", "-ep", type=int, default=10, help="number of epochs"
    )
    arg_parser.add_argument(
        "--gpu_batch", "-gb", type=int, default=24, help="batch size per gpu"
    )
    arg_parser.add_argument(
        "--resume_path",
        "-rp",
        type=str,
        default=None,
        help="Path to weights for resume",
    )
    arg_parser.add_argument(
        "--use_pretrained",
        "-up",
        type=bool,
        default=False,
        help="Flag to use resume_path not to resume from, but as pretrained weights for a new experiment",
    )
    arg_parser.add_argument(
        "--override_name",
        "-on",
        type=str,
        default=None,
        help="Optionally override experiment name",
    )
    arg_parser.add_argument(
        "--random_weights",
        "-rw",
        type=bool,
        default=False,
        help="If set, the model will be initialized with random weights (i.e train fully from scratch)"
    )
    arg_parser.add_argument(
        "--learning_rate",
        "-lr",
        type=bool,
        default=False,
        help="If set, the model will be trained using learning rate decay"
    )
    args = arg_parser.parse_args()

    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_usage

    experiment_name = args.config_path.split("/")[-2]
    if (args.override_name != None):
        experiment_name = args.override_name

    # check wether to resume with these weights, or to use as pretrained
    res_decision = False
    if (args.resume_path != None) and (args.use_pretrained == False):
        res_decision = True

    model = YOLO("yolov5lu.pt")
    if args.resume_path != None:
        model = YOLO(args.resume_path)
    if args.random_weights == True:
        # ! important: .yaml means this is just a config, not preloaded weights
        model = YOLO("yolov5l.yaml")
    if args.learning_rate == True:
        model.train(
            data=args.config_path,
            lr0 = 1e-3,
            lrf = 1e-4,
            epochs=args.epochs,
            name=experiment_name,
            device=[int(x) for x in args.gpu_usage.split(",")],
            batch=len(args.gpu_usage.split(",")) * args.gpu_batch,
            resume=res_decision,
        )
    else:
        model.train(
            data=args.config_path,
            epochs=args.epochs,
            name=experiment_name,
            device=[int(x) for x in args.gpu_usage.split(",")],
            batch=len(args.gpu_usage.split(",")) * args.gpu_batch,
            resume=res_decision,
        )


if __name__ == "__main__":
    main()
