"""
Data loading and unit partitioning module for 700 English Vocabulary Web App.
Supports loading default JSON, uploaded CSV, uploaded JSON, and unit chunking.
"""

import json
import csv
import io
from typing import List, Dict, Any, Tuple
import pandas as pd

REQUIRED_FIELDS = ["word", "pos", "chinese_meaning"]
STANDARD_FIELDS = ["id", "unit", "word", "phonetic", "pos", "english_definition", "chinese_meaning", "example_sentence"]

def load_default_vocab(file_path: str = "data/default_vocab.json") -> List[Dict[str, Any]]:
    """Loads the built-in 700-word dataset."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return partition_units(data)
    except Exception as e:
        print(f"Error loading default vocabulary: {e}")
        return []

def partition_units(vocab_list: List[Dict[str, Any]], words_per_unit: int = 10) -> List[Dict[str, Any]]:
    """Partitions vocabulary list into units of N words (default 10)."""
    updated_list = []
    for idx, item in enumerate(vocab_list, 1):
        item_copy = dict(item)
        item_copy["id"] = idx
        item_copy["unit"] = ((idx - 1) // words_per_unit) + 1
        # Normalize fields
        item_copy["word"] = str(item_copy.get("word", "")).strip()
        item_copy["phonetic"] = str(item_copy.get("phonetic", "")).strip() or f"/{item_copy['word']}/"
        item_copy["pos"] = str(item_copy.get("pos", "")).strip() or "n."
        item_copy["english_definition"] = str(item_copy.get("english_definition", "")).strip()
        item_copy["chinese_meaning"] = str(item_copy.get("chinese_meaning", "")).strip()
        item_copy["example_sentence"] = str(item_copy.get("example_sentence", "")).strip()
        updated_list.append(item_copy)
    return updated_list

def parse_uploaded_file(uploaded_file) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Parses and validates user uploaded CSV or JSON file.
    Returns: (success_bool, message, data_list)
    """
    if uploaded_file is None:
        return False, "未選取檔案", []

    filename = uploaded_file.name.lower()
    raw_bytes = uploaded_file.getvalue()

    try:
        if filename.endswith(".json"):
            content = raw_bytes.decode("utf-8")
            data = json.load(io.StringIO(content))
            if not isinstance(data, list):
                return False, "JSON 格式錯誤：根節點必須是單字物件陣列 (Array of Objects)", []
            
            # Validate items
            validated = []
            for idx, item in enumerate(data, 1):
                if not isinstance(item, dict) or not item.get("word"):
                    continue
                validated.append({
                    "word": str(item.get("word", "")).strip(),
                    "phonetic": str(item.get("phonetic", "")).strip(),
                    "pos": str(item.get("pos", "")).strip(),
                    "english_definition": str(item.get("english_definition", "")).strip(),
                    "chinese_meaning": str(item.get("chinese_meaning", "")).strip(),
                    "example_sentence": str(item.get("example_sentence", "")).strip()
                })
            
            if not validated:
                return False, "JSON 檔案中找不到有效的單字資料", []
            
            partitioned = partition_units(validated)
            return True, f"成功載入 {len(partitioned)} 個單字（共 {partitioned[-1]['unit']} 個單元）！", partitioned

        elif filename.endswith(".csv"):
            try:
                content = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = raw_bytes.decode("big5", errors="ignore")
                
            df = pd.read_csv(io.StringIO(content))
            # Column normalization
            col_map = {}
            for col in df.columns:
                c_clean = col.strip().lower().replace(" ", "_")
                if "word" in c_clean or "單字" in col:
                    col_map[col] = "word"
                elif "phonetic" in c_clean or "音標" in col:
                    col_map[col] = "phonetic"
                elif "pos" in c_clean or "詞性" in col or "part" in c_clean:
                    col_map[col] = "pos"
                elif "english" in c_clean or "eng" in c_clean or "英英" in col:
                    col_map[col] = "english_definition"
                elif "chinese" in c_clean or "chi" in c_clean or "中文" in col or "釋義" in col or "meaning" in c_clean:
                    col_map[col] = "chinese_meaning"
                elif "example" in c_clean or "sentence" in c_clean or "例句" in col:
                    col_map[col] = "example_sentence"
            
            df = df.rename(columns=col_map)
            if "word" not in df.columns:
                return False, "CSV 缺少必要的 'word' 欄位！請參考範本格式。", []
            
            validated = []
            for _, row in df.iterrows():
                w = str(row.get("word", "")).strip()
                if not w or w.lower() == "nan":
                    continue
                validated.append({
                    "word": w,
                    "phonetic": "" if pd.isna(row.get("phonetic")) else str(row.get("phonetic", "")).strip(),
                    "pos": "" if pd.isna(row.get("pos")) else str(row.get("pos", "")).strip(),
                    "english_definition": "" if pd.isna(row.get("english_definition")) else str(row.get("english_definition", "")).strip(),
                    "chinese_meaning": "" if pd.isna(row.get("chinese_meaning")) else str(row.get("chinese_meaning", "")).strip(),
                    "example_sentence": "" if pd.isna(row.get("example_sentence")) else str(row.get("example_sentence", "")).strip()
                })
                
            if not validated:
                return False, "CSV 檔案中找不到有效的單字資料", []
            
            partitioned = partition_units(validated)
            return True, f"成功載入 {len(partitioned)} 個單字（共 {partitioned[-1]['unit']} 個單元）！", partitioned

        else:
            return False, "不支援的檔案格式，請上傳 .csv 或 .json 檔案", []

    except Exception as e:
        return False, f"檔案解析失敗: {str(e)}", []

def get_unit_words(vocab_list: List[Dict[str, Any]], unit_id: int) -> List[Dict[str, Any]]:
    """Retrieves all words belonging to a specific unit."""
    return [w for w in vocab_list if w.get("unit") == unit_id]

def get_total_units(vocab_list: List[Dict[str, Any]]) -> int:
    """Gets total unit count based on dataset."""
    if not vocab_list:
        return 0
    return vocab_list[-1].get("unit", 1)

def search_vocabulary(vocab_list: List[Dict[str, Any]], keyword: str, pos_filter: str = "All") -> List[Dict[str, Any]]:
    """Searches vocabulary by keyword (word, chinese meaning, english definition) and optional POS filter."""
    if not keyword and pos_filter == "All":
        return vocab_list

    kw = keyword.lower().strip()
    results = []
    for w in vocab_list:
        # Check POS filter
        if pos_filter != "All" and w.get("pos", "").lower() != pos_filter.lower():
            continue
        
        # Check Keyword match
        if not kw:
            results.append(w)
            continue
            
        word_match = kw in w.get("word", "").lower()
        chi_match = kw in w.get("chinese_meaning", "").lower()
        eng_match = kw in w.get("english_definition", "").lower()
        
        if word_match or chi_match or eng_match:
            results.append(w)
            
    return results
