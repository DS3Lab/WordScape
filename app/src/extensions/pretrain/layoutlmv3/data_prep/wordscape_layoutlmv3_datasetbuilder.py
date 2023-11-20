from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List
from datasets import GeneratorBasedBuilder, Value, Sequence, ClassLabel, Features, DatasetDict, SplitGenerator, Image, DownloadMode
from datasets.download.download_manager import DownloadManager
from datasets.info import DatasetInfo
import multiprocessing as mp
import numpy as np

@dataclass
class WSLayoutLMDataPoint():

    id: str
    tokens: List[str]
    word_bboxes: List[List[int]]
    entity_bboxes: List[List[int]]
    entity_labels: List[int]
    image: np.ndarray


class WSLayoutLMDataBuilder(GeneratorBasedBuilder):
    
    def __init__(self, entity_label_names: List[str]):
        self.entity_label_names = entity_label_names
        print(self.entity_label_names)
        # need to do this before super, since super updates using _info
        super(WSLayoutLMDataBuilder, self).__init__()

        self.id_data = []
        self.tokens_data = []
        self.word_bboxes_data = []
        self.entity_bboxes_data = []
        self.entity_labels_data = []
        self.image_data = []

    def _info(self) -> DatasetInfo:
        # ! dataset feature info; datapoint class must match this
        features = Features({
            "id": Value(dtype='string'),
            "tokens": Sequence(feature=Value(dtype='string')),
            "word_bboxes": Sequence(feature=Sequence(feature=Value(dtype='int64'))),
            "entity_bboxes": Sequence(feature=Sequence(feature=Value(dtype='int64'))),
            "entity_labels": Sequence(feature=ClassLabel(names=self.entity_label_names)),
            "image": Image()
        })
        return DatasetInfo(features=features)
    
    def _split_generators(self, dl_manager: DownloadManager):
        return [
            SplitGenerator(name="data", gen_kwargs={"id": self.id_data, "tokens": self.tokens_data, "word_bboxes": self.word_bboxes_data, 
                                                          "entity_bboxes": self.entity_bboxes_data, "entity_labels": self.entity_labels_data,
                                                          "image": self.image_data})
        ]
    
    def _generate_examples(self, id, tokens, word_bboxes, entity_bboxes, entity_labels, image):
        for (i, t, wb, eb, el, img) in zip(id, tokens, word_bboxes, entity_bboxes, entity_labels, image):
            print(img)
            yield i, {
                "id": i,
                "tokens": t,
                "word_bboxes": wb,
                "entity_bboxes": eb,
                "entity_labels": el,
                "image": img
            }
    
class WSLayoutLMDataCollectorProcess(mp.Process):

    def __init__(self, entity_label_names: List[str], in_q: mp.Queue, proc_to_wait: int, out_q: mp.Queue, out_path: Path):
        r"""A class to receive datapoints from dataset build workers, and add these to a huggingface 
        format dataset object, which is later saved to disk."""
        super(WSLayoutLMDataCollectorProcess, self).__init__()

        self.builder = WSLayoutLMDataBuilder(entity_label_names=entity_label_names)
        self.in_q = in_q
        self.proc_to_wait = proc_to_wait
        self.out_q = out_q
        self.out_path = out_path
        self.ingested_count = 0

    def _ingest_datapoint(self, datapoint: WSLayoutLMDataPoint):
        self.builder.id_data.append(datapoint.id)
        self.builder.tokens_data.append(datapoint.tokens)
        self.builder.word_bboxes_data.append(datapoint.word_bboxes)
        self.builder.entity_bboxes_data.append(datapoint.entity_bboxes)
        self.builder.entity_labels_data.append(datapoint.entity_labels)
        self.builder.image_data.append(datapoint.image)
        
        # track total ingested datapoints
        self.ingested_count += 1
        print("ingested datapoint " + str(self.ingested_count))
        
    def get_count(self) -> int:
        return self.ingested_count

    def run(self):
        # consume in_q datapoints, until we see proc_to_wait stop signals (enqueued None)
        seen_stop_sigs = 0
        while True:
            input = self.in_q.get(block=True, timeout=None)
            if input is None:
                seen_stop_sigs += 1
                print("seen stop sigs " + str(seen_stop_sigs))

                if seen_stop_sigs >= self.proc_to_wait:
                    # write dataset to disk
                    # ! IMPORTANT need to force redownload here, otherwise it just reuses the cached old dataset
                    self.builder.download_and_prepare(download_mode=DownloadMode.FORCE_REDOWNLOAD, ignore_verifications=True)
                    dataset = self.builder.as_dataset()
                    dataset_dict = DatasetDict({
                        "data": dataset
                    })
                    dataset_dict.save_to_disk(self.out_path)
                    break

            else:
                self._ingest_datapoint(input)
