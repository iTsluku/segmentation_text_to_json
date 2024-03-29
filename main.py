import json
import os
import re
import numpy as np
from pathlib import Path

from special_court_munich.corpus import CorpusStats
from special_court_munich.process_document import text_segmentation_alg

pattern_file_with_segments = re.compile(r"^.*\d+_\d{5}.(?:txt|hocr)$")
pattern_filename_id = re.compile(r"^.*\d+_(\d{5}).(?:txt|hocr)$")


def main(debug=False) -> None:
    cwd = os.getcwd()
    output_path_abs = os.path.join(cwd, "output/2023_02_output.json")
    corpus_stats = CorpusStats()
    data = {"proceedings": []}
    if debug:
        data["stats"]: {}
    Path(os.path.join(cwd, "output")).mkdir(parents=True, exist_ok=True)
    # change input dir path here
    text_new_dir_path = os.path.join(cwd, "input/07_HOCR")
    text_directory = os.fsencode(text_new_dir_path)

    ids_and_filenames = []  # (id,file)
    for file in os.listdir(text_directory):
        filename = os.fsdecode(file)
        # filter Register, Info, ...
        match = pattern_file_with_segments.search(filename)
        if not match:
            continue
        document_id = pattern_filename_id.findall(filename)[0]
        ids_and_filenames.append((int(document_id), filename))
    ids_and_filenames.sort(key=lambda x: x[0])

    forward_pass = []
    for i, (document_id, filename) in enumerate(ids_and_filenames):
        proceedings, corpus_stats, forward_pass = text_segmentation_alg(
            os.path.join(text_new_dir_path, filename),
            filename,
            str(document_id),
            corpus_stats,
            forward_pass,
        )
        for p in proceedings:
            data["proceedings"].append(p)

    # eval proceeding_id
    if data["proceedings"]:
        prev_proceeding_id = int(data["proceedings"][0]["proceeding"]["ID"])
        for proceeding in data["proceedings"]:
            if proceeding["proceeding"]["ID"]:
                proceeding_id = int(proceeding["proceeding"]["ID"])
                if proceeding_id > prev_proceeding_id + 1:
                    # wrong proceeding_id or just missing proceeding --test for OCR fail
                    # TODO correct or remove proceeding_id, if its bigger then next available proceeding or smaller than prev
                    # 3,992,5 -> 3,4,5
                    # TODO if rm, then mark for manual fix (doesn't occur that often!)
                    """
                    print(
                        f"{prev_proceeding_id=} {proceeding_id=} add:{proceeding_id - prev_proceeding_id - 1}"
                    )
                    """
                prev_proceeding_id = proceeding_id

        # add info about missing proceedings
        # estimate: get last 20 proceedings IDs (pot. None),
        # take median to reduce chance of using ocr fail min-max outlier
        id_max_estimate = int(
            np.median(
                [
                    int(p["proceeding"]["ID"])
                    for p in [
                        x
                        for x in [
                            d
                            for d in data["proceedings"][-20:]
                            if d["proceeding"]["ID"]
                        ]
                    ]
                ]
            )
        )
        proceedings_no = len(data["proceedings"])
        for _ in range(id_max_estimate - proceedings_no):
            corpus_stats.inc_val_missing_proceedings()

    if debug:
        data["stats"] = corpus_stats.get_repr_dict()

    # print(len(data["proceedings"]))

    with open(output_path_abs, mode="w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


if __name__ == "__main__":
    main(debug=False)
