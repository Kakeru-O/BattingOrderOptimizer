import sys
import os
import pandas as pd
import shutil

# プロジェクトのルートディレクトリをPythonのパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# テスト対象のモジュールをインポート
import app.utils.get_player_data as gpd
import app.utils.add_speed_score as ass

# --- テスト設定 ---
DUMMY_DIR = "./tests/dummy_data_for_pipeline"
DUMMY_RAW_DIR = os.path.join(DUMMY_DIR, "raw")
DUMMY_PROCESSED_DIR = os.path.join(DUMMY_DIR, "processed")
YEAR = "2024"
TEAM = "test"

def setup_module(module):
    """テストの前にダミーディレクトリとファイルを作成"""
    os.makedirs(DUMMY_RAW_DIR, exist_ok=True)
    os.makedirs(DUMMY_PROCESSED_DIR, exist_ok=True)
    # ダミーのrawデータを作成
    raw_content = "選手,試合,打席,打数,得点,安打,二塁打,三塁打,本塁打,塁打,打点,盗塁,盗塁刺,犠打,犠飛,四球,故意四,死球,三振,併殺打,打率,長打率,出塁率\nPlayerA,10,50,40,5,12,2,1,1,18,5,3,1,0,1,8,0,1,10,1,.300,.450,.420\nPlayerB,10,50,45,8,11,3,0,2,20,8,0,0,1,0,4,0,0,15,2,.250,.444,.311"
    with open(os.path.join(DUMMY_RAW_DIR, f"{YEAR}_{TEAM}.csv"), "w") as f:
        f.write(raw_content)

def teardown_module(module):
    """テストの後にダミーディレクトリをクリーンアップ"""
    if os.path.exists(DUMMY_DIR):
        shutil.rmtree(DUMMY_DIR)

def test_data_processing_pipeline():
    """データ加工のパイプライン全体をテストする"""
    # 1. get_player_dataのメイン処理を実行
    gpd.main(teams=[TEAM], year=YEAR, raw_dir=DUMMY_RAW_DIR, processed_dir=DUMMY_PROCESSED_DIR)

    # processedファイルが作成されたか確認
    processed_file = os.path.join(DUMMY_PROCESSED_DIR, f"{YEAR}_{TEAM}.csv")
    assert os.path.exists(processed_file)

    # 中身を確認
    df_processed = pd.read_csv(processed_file)
    assert 'Ground_Out_ratio' in df_processed.columns
    assert df_processed.shape[0] == 2 # 2選手いるはず

    # 2. add_speed_scoreのメイン処理を実行
    ass.main(teams=[TEAM], year=YEAR, raw_dir=DUMMY_RAW_DIR, processed_dir=DUMMY_PROCESSED_DIR)

    # Speedスコアが追加されたか確認
    df_final = pd.read_csv(processed_file)
    assert 'Speed' in df_final.columns
    # 値の検証
    player_a_speed = df_final[df_final['Player'] == 'PlayerA']['Speed'].iloc[0]
    expected_speed = 1*3 + 3*1 - 1*2 # 3B*3 + SB*1 - CS*2
    assert player_a_speed == expected_speed

    print("\n✅ test_data_processing_pipeline passed.")

if __name__ == "__main__":
    setup_module(None)
    test_data_processing_pipeline()
    teardown_module(None)
    print("\n--- Test script finished successfully ---")