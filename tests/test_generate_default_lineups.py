import sys
import os
import pandas as pd
import shutil

# プロジェクトのルートディレクトリをPythonのパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils.generate_default_lineups import generate_and_save_default_lineups

# テスト用の出力ディレクトリ
TEST_OUTPUT_DIR = "./tests/temp_output"
TEST_YEAR = "2023" # テスト対象の年度
TEST_OUTPUT_FILE = os.path.join(TEST_OUTPUT_DIR, f"default_lineups_{TEST_YEAR}.csv")

def setup_module(module):
    """テストの前にディレクトリを作成"""
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)

def teardown_module(module):
    """テストの後にディレクトリをクリーンアップ"""
    if os.path.exists(TEST_OUTPUT_DIR):
        shutil.rmtree(TEST_OUTPUT_DIR)

def test_generate_and_save_default_lineups():
    """デフォルトスタメンが生成され、CSVとして保存されるかテスト"""
    generate_and_save_default_lineups(year=TEST_YEAR, output_dir=TEST_OUTPUT_DIR)

    # CSVファイルが作成されたか確認
    assert os.path.exists(TEST_OUTPUT_FILE)

    # CSVファイルの内容を確認
    df_lineups = pd.read_csv(TEST_OUTPUT_FILE)
    print("\n--- df_lineups dtypes ---")
    print(df_lineups.dtypes)
    print("\n--- df_lineups head ---")
    print(df_lineups.head())
    assert not df_lineups.empty
    assert 'Year' in df_lineups.columns
    assert 'League' in df_lineups.columns
    assert 'Team' in df_lineups.columns
    assert 'Team_Abbr' in df_lineups.columns
    assert 'Position' in df_lineups.columns
    assert 'Player' in df_lineups.columns

    # 特定のチームのデータが存在するか (例: ロッテ)
    marines_lineup = df_lineups[(df_lineups['Team_Abbr'] == 'M') & (df_lineups['Year'] == TEST_YEAR)]
    assert not marines_lineup.empty
    assert len(marines_lineup) == 9 # パ・リーグなので9人

    # 特定のチームのデータが存在するか (例: 巨人)
    giants_lineup = df_lineups[(df_lineups['Team_Abbr'] == 'G') & (df_lineups['Year'] == TEST_YEAR)]
    assert not giants_lineup.empty
    assert len(giants_lineup) == 8 # セ・リーグなので8人

    print("\n✅ test_generate_and_save_default_lineups passed.")

if __name__ == "__main__":
    setup_module(None)
    test_generate_and_save_default_lineups()
    teardown_module(None)
    print("\n--- Test script finished successfully ---")
