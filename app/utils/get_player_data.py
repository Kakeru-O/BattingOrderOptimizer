import os
#import requests
#import urllib  #HTMLにアクセス＆取得
#from bs4 import BeautifulSoup #HTMLからデータ抽出
import pandas as pd
import numpy as np

def get_data(team:str, year:str):

    # URLを指定
    url = f'https://npb.jp/bis/{year}/stats/idb1_{team}.html'

    # HTMLからテーブルを読み込む
    tables = pd.read_html(url)

    # 最初のテーブルを取得
    df = tables[0]
    df = df.loc[1:,1:].reset_index(drop=True)
    df.columns = df.iloc[0]
    # 半角スペースを削除
    df.columns = df.columns.str.replace(' ', '', regex=False)
    # 半角スペース、全角スペース、改行コードを削除
    df.columns = df.columns.str.replace(r'[\s\u3000]', '', regex=True)

    df = df.loc[1:].reset_index(drop=True)
    
    # 列ごとに型変換を試みる
    for col in df.columns[1:]:
        # 数値変換を試みる
        try:
            # 一度 float 型に変換
            temp_col = pd.to_numeric(df[col], errors='coerce')
            # NaN のない整数値のみなら int 型に変換
            if temp_col.dropna().mod(1).eq(0).all():
                df[col] = temp_col.astype('Int64')  # 欠損値対応の int 型
            else:
                df[col] = temp_col  # float 型のまま
        except ValueError:
            # 数値変換できない場合はそのまま
            pass

    df['選手'] = df['選手'].str.replace(r'\s+', '', regex=True)

    csv_path = f"./data/raw/{year}_{team}.csv"
    df.to_csv(csv_path,index=False)

    return df

def process_data(df,team,year):
    # 現在のスクリプトのディレクトリを取得
    # current_dir = os.path.dirname(__file__)

    # # CSVファイルのパスを指定
    # path_team = {"M":"../data/lotte_2024.csv"}
    # csv_path = os.path.join(current_dir, path_team[team])

    # 列名を置き換え
    eng_columns = [
        'Player', 'G', 'PA', 'AB', 'R', 'H', '2B', '3B', 'HR', 'TB', 'RBI',
        'SB', 'CS', 'SH', 'SF', 'BB', 'IBB', 'HBP', 'SO', 'GIDP', 'AVG', 'SLG','OBP'
    ]
    df.columns = eng_columns

    # 一塁打を計算して追加
    df['1B'] = df['H'] - (df['2B'] + df['3B'] + df['HR'])
    # 四死球を計算して追加
    df['BB+HBP'] = df['BB'] + df['HBP']
    # OPS
    df['OPS'] = df['SLG'] + df['OBP']
    
    # 各種割合の計算
    df['1B_ratio'] = df['1B'] / df['PA']
    df['2B_ratio'] = df['2B'] / df['PA']
    df['3B_ratio'] = df['3B'] / df['PA']
    df['HR_ratio'] = df['HR'] / df['PA']
    df['BB+HBP_ratio'] = df['BB+HBP'] / df['PA']

    # アウトの計算
    df['Out'] = df['PA'] - (df['H'] + df['BB'] + df['HBP'] + df['IBB'])

    # ホームラン,3B,2Bが０の人に微小な確率を付与
    df.loc[df["HR_ratio"]==0,"1B_ratio"] -= 1e-4
    df.loc[df["3B_ratio"]==0,"1B_ratio"] -= 1e-4
    df.loc[df["2B_ratio"]==0,"1B_ratio"] -= 1e-4
    df.loc[df["HR_ratio"]==0,"HR_ratio"] = 1e-4
    df.loc[df["3B_ratio"]==0,"3B_ratio"] = 1e-4
    df.loc[df["2B_ratio"]==0,"2B_ratio"] = 1e-4

    # アウトの割合
    # df['Out_ratio'] = df['Out'] / df['PA']
    df['Out_ratio'] = 1 - df['1B_ratio'] - df['2B_ratio'] - df['3B_ratio'] - df['HR_ratio'] - df['BB+HBP_ratio']

    # 50打席以上に限定
    df = df[df["PA"]>=50].sort_values("PA",ascending=False).reset_index(drop=True)

    # 最終の出力
    df_res = df[["Player","1B_ratio","2B_ratio","3B_ratio","HR_ratio","BB+HBP_ratio","Out_ratio"]].reset_index(drop=True)
    
    df_res.to_csv(f"./data/processed/{year}_{team}.csv",index=False)
    return df_res



if __name__ == "__main__":
    year = "2024"
    team_list = ["g","t","c","db","s","d","f","e","m","l","b","h"]
    for team in team_list:
        print(team)
        df = get_data(team, year)
        df_res = process_data(df, team, year)
    