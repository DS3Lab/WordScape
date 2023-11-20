# Extensions
The pipeline extensions can be used to create and filter custom datasets from the raw WordScape output. The 
configurations are specified in json files located in `configs/extensions/` and the script that can be used to filter 
the raw data is in `src/extensions/obj_detection/spaceml/ws_yolo_dataprep.py` which creates a dataset compatible 
with the YOLO format. 

## Configure dataset parameters

Each dataset is specified by a `.json` config file. This contains the `name` field (the name of the dataset), as well as the `train_settings` and `val_settings` objects. These two objects define the settings for the training and validation datasets, specifically. An example `train_settings` configuration is given below:

```json
{
    "train_settings": {
        "raw_path": "/mnt/DATA/msc-data/cc_main_2023_14/train",
        "is_validation": false,
        "max_img": 200000,
        "elem_drops": [14, 28, 29],
        "elem_mergings": {
            "masters": {
                "1": "heading_title_global",
                "10": "text_merged",
                "11": "list_merged",
                "17": "table_cell_merged"
            },
            "mapping": {
                "0": "1",
                "2": "1",
                "3": "1",
                "4": "1",
                "5": "1",
                "6": "1",
                "7": "1",
                "8": "1",
                "9": "1",
                "15": "17",
                "18": "11",
                "19": "11",
                "20": "10",
                "23": "10"
            }
        },
        "elem_mins": {
            "1": 20000,
            "10": 20000,
            "11": 20000,
            "12": 20000,
            "13": 20000,
            "16": 20000,
            "17": 20000,
            "21": 20000,
            "22": 20000,
            "26": 20000
        },
        "scanify": false,
        "quality_threshold": 0.7,
        "language_codes": ["es", "fr", "it", "de", "pt", "en"],
        "language_code_threshold": 0.75
    }
}
```

- The `raw_path` parameter is the path to the directory containing the base annotated WordScape data. This directory is required to conform to the WordScape directory format, particularly the `meta` and `multimodal` directories.

- The `max_img` parameter specifies the size of the dataset.

- The `elem_drops` parameter specifies a list of WordScape entity IDs to drop. In the above example, these are 14 (`table_header`), 28 (`table_row`) and 29 (`table_column`). For all entity IDs, see the `settings` module.

- The `elem_mergings` object specifies which WordScape entity classes should be mapped to another entity class; keys of the `mapping` object are mapped to values. The `masters` object specifies the name of the new merged class. Note that any entity ID appearing as a value in the `mapping` object must contain an entry in the `masters` object.

- The `elem_mins` object specifies the minimum number of representative pages for a given entity ID. The above entry of `"1": 20000` guarantees that at least 20'000 pages which contain at least one entity of class 1 will be contained in the resulting dataset, given that enough such pages exist above the configured quality threshold and conformant to the language filter. Note that this takes `elem_mergings` into account; in the above example, entity ID 2 is mapped to 1, so an entry in `elem_mins` with entity ID 2 as its key would have no effect.

- The `scanify` parameter, if set to true, configures the augmentation of the page images using the `augraphy` library.

- The `quality_threshold` parameter is the minimum WordScape annotation quality metric that a page must meet to be considered for inclusion into the dataset.

- The `language_codes` parameter defines a list of languages (based on extraction via `fasttext`). One of the configured languages must be the main content language of a page for that page to be considered for inclusion into the dataset.

- The `language_code_threshold` parameter defines the minimum confidence of the `fasttext` content language prediction for a page to be considered for inclusion into the dataset.

## Run dataset creation

Once a configuration has been created, to create a dataset for a `YOLO` model, run:

```bash
python ./src/extensions/obj_detection/spaceml/ws_yolo_dataprep.py -ec path_to_config.json -op path_to_output_dataset -np 1
```

Note that the `np` argument specifies the number of processes used by the dataset creator; this can be increased to speed up creation.

# Training a YOLOv5 model

After a training dataset has been created, train the YOLOv5l model by running:

```bash
OMP_NUM_THREADS=12 python -m torch.distributed.run --nproc_per_node 6 ./src/extensions/obj_detection/spaceml/ws_yolo_experimentrun.py \
-cp /mnt/scratch/thannerv/msc-data/my_yolo_data/dataset.yaml -gu "2,3,4,5,6,7" -gb 8 -ep 45  \
-on "my_experiment_name" -rw 1
```

- The `OMP_NUM_THREADS=12` and `-m torch.distributed.run` settings are recommended for running pytorch models in a multi-GPU setting.

- The `nproc_per_node` argument must match the number of GPUs employed.

- The `cp` argument is the path to the dataset config file (created in the previous step).

- The `gu` argument specifies the GPU IDs to use in training.

- The `gb` argument specifies the batch size to use, per employed GPU.

- The `ep` argument specifies the number of training epochs.

- The `on` argument optionally sets a custom experiment name.

- The `rw` flag, if set, initializes training from random weights (as opposed to the pretrained `YOLO` weights).

Finetuning using pretrained weights is also possible:

```bash
OMP_NUM_THREADS=12 python -m torch.distributed.run --nproc_per_node 6 ./src/extensions/obj_detection/ws_yolo_experimentrun.py \
-cp /mnt/scratch/thannerv/msc-data/yolo_xfund/zh/dataset.yaml -gu "2,3,4,5,6,7" -gb 8 -ep 45 \
-rp "/home/thannerv/msc-thesis/runs/detect/1header_balanced_quality/weights/best.pt" -on "yolo_xfund_zh_pre200k" -up 1 -lr 1
```

- The `rp` argument gives the path to the pretrained weights (stored in a `.pt` file) from which to begin finetuning.

- The `up` flag, if set, configures a finetuning run. If this flag is not set, but an argument is provided for `rp`, training is instead resumed.

- The `lr` flag toggles learning rate decay when set.

# Other Extensions

To format a WordScape dataset for training / pretraining in the LayoutLMv3 format, run:

```bash
python ./src/extensions/pretrain/layoutlmv3/data_prep/wordscape_layoutlmv3_dataprep.py -ec path_to_config.json -op path_to_output_dataset
```

The output dataset can be configured the same way as described in "Configure dataset parameters". This will produce a dataset
conformant to the `huggingface dataset` library. This dataset can therefore be used together with the [Huggingface LayoutLMv3 implementation](https://huggingface.co/docs/transformers/model_doc/layoutlmv3).

To format the PubLayNet dataset into a YOLO-compatible format, first download the PubLayNet full dataset from [this link](https://developer.ibm.com/exchanges/data/all/publaynet/).

Once this is downloaded, run:

```bash
python ./src/extensions/obj_detection/data_prep/publaynet_yolo_formatter.py -pp path_to_publaynet_dir -op path_to_output_dataset
```

To format the DocLayNet dataset into a YOLO-compatible format, first download the DocLayNet Core dataset from [this link](https://developer.ibm.com/exchanges/data/all/doclaynet/).

Once this is downloaded, run:

```bash
python ./src/extensions/obj_detection/data_prep/doclaynet_yolo_formatter.py -dp path_to_doclaynet_core_dir -op path_to_output_dataset
```

To create smaller YOLO-datasets (e.g to create a 20k-size YOLO dataset from the 80k full DocLayNet dataset), we use a script to move images and labels to an alternate folder. To do this, run the script:

```bash
python ./src/extensions/obj_detection/spaceml/move_train_data_singlefiles.py -sd dir_to_move_files_from -sd dir_to_move_files_to -n num_files_to_move
```

Note that the `-sd` argument should be set to either a `train` or a `val` directory of an already created YOLO-dataset.
