#!/usr/bin/env python3
from pathlib import Path
import subprocess as sp
import soundfile as sf
import re

# [!]SEVEN-BRIDGEコンバータに比べればまだ汎用性は考えてあるものの、それでも解析途中です
# これをそのまま他作品に使い回さないでください

# voiceディレクトリ内メモ
# 1.令嬢
# 2.司書
# 3.法師
# 4.渡し守
# 5.お手伝いさん


# デバッグモード
DEBUG_MODE = 0


# ディレクトリの存在チェック関数
def dir_check(path_list):

	CHK = True
	for p in path_list:
		if not p.exists():
			print('ERROR: "' + str(p) + '" is not found!')
			CHK = False
			
	return CHK


# シナリオを平文にデコードする関数
def text_dec(gsc_exe, scr, scr_dec):

	#デコード先のディレクトリを作成
	scr_dec.mkdir(parents=True, exist_ok=True)

	#gsc除外リスト作成 - kagerou専用
	ex_gsc = ['0000', '0001', '0040', '0099', '9999']

	#gscをglob
	for p in scr.glob('*.gsc'):
	
		#不要gscはここで除外
		if not (str(p.stem) in ex_gsc):

			#デコード処理(ライセンスとか面倒なのでsubprocessで、ネイティブで動かしたい人は勝手に作って)
			sp.run([str(gsc_exe), '-m', 'decompile', '-i', str(p)], shell=True, cwd=scr_dec )

	#txt(さっきデコードしたやつ)をglob
	for p in scr.glob('*.txt'):

		#scr_decへ移動(Pathlibのrenameを利用)
		p_move = (scr_dec / p.name)
		p.rename(p_move)

	return

# 音楽変換関数
def sound_dec(decode_list):

	#リスト内のディレクトリパスでfor
	for d in decode_list:

		#ディレクトリパス内のファイル一覧でfor
		for p in d.glob('**/*.ogg'):

			#wav化した際のパスを作成
			p_wav = p.with_suffix('.wav')

			#wavがまだない場合に限り処理
			if not p_wav.exists():
				
				#ogg読み込み
				sd = sf.read(p)

				#wavに変換
				sf.write(p_wav, sd[0], sd[1])

				#元のoggを削除
				p.unlink()

	return


# txt置換→0.txt出力関数
def text_cnv(default, zero_txt, scr_dec, path_dict_keys):

	#シナリオ文判定初期化
	mes_max = 0
	movie_cnt = 1

	#default.txtを読み込み
	with open(default, encoding='cp932', errors='ignore') as f:
		txt = f.read()

	#デコード済みtxtをforで回す
	for p in scr_dec.glob('*.txt'):

		#デコード済みtxtを読み込み
		with open(p, encoding='cp932', errors='ignore') as f:

			#デコード済みtxt一つごとに開始時改行&サブルーチン化
			if DEBUG_MODE:
				txt += '\n;--------------- '+ str(p.name) +' ---------------'
			txt += '\n*SCR_'+ str(p.stem).replace('.', '_') +'\n\n'

			#シナリオ文判定初期化
			line_message = False
			mes_cnt = 0

			for line in f:

				line_hash = re.search(r'#([A-z0-9]+?)\n', line)# "#xxxx~" みたいな命令文
				line_label = re.search(r'\@([0-9]+)', line)# "@(数字)" JUMPの飛び先 ラベル

				#前の行及び今の行のシナリオ文判定
				last_message = line_message
				line_message = False

				#空行 - そのまま放置
				if re.match('\n', line):
					pass

				#>-1とか - なんだろうこれ
				elif re.match(r'>', line):
					line = (';' + line) if DEBUG_MODE else ''

				#select命令
				elif re.match(r'select', line):
					line = 'RSC_select\n'

				#ディレクトリ名呼び出し系
				elif (line.replace('\n', '')) in path_dict_keys:
					line = (';' + line) if DEBUG_MODE else ''

				#命令文 - "last_hash"変数に保持
				elif line_hash:
					line = (';' + line) if DEBUG_MODE else ''
					last_hash = line_hash[1]

				#JUMPの飛び先はNSCのラベル仕様に置換
				elif line_label:
					line = ('*JUMP_' + line_label[1] + '_' + str(p.stem).replace('.', '_') +'\n')

				#命令文の次の行
				elif last_hash:

					#命令の引数(?)を配列に変換しconvert_listへ代入
					try:
						convert_list = eval(line.replace('\n', ''))
					except:
						convert_list = False

					#失敗した失敗した失敗した配列変換に失敗した
					if not convert_list:
						
						if (r'[]' in line):

							#IMAGE_SET スプライト除去(こいつ基本空配列なんで)
							if last_hash == 'IMAGE_SET':
								line = ('csp -1:print 10' + '\n')

						else:

							#空配列変換失敗はありがちなので除外
							print('CnvListErr:' + line.replace('\n', ''))

						if not (last_hash == 'IMAGE_SET'):
							line = (';' + line) if DEBUG_MODE else ''

					#MESSAGE メッセージ表示&ボイス
					elif last_hash == 'MESSAGE':

						#convert_listからボイスの有無を取得
						voice_num = convert_list[1]

						#あれば命令化、なければ無視 - kagerou専用
						if len(str(voice_num)) == 5:
							line = 'RSC_MESSAGE "' + str(voice_num)[0] + '\\' + str(voice_num)[1:] + '"\n'#最初の1桁がディレクトリ、残り4がファイル名
						else:
							line = (';' + line) if DEBUG_MODE else ''

					#PAUSE 待ち
					elif last_hash == 'PAUSE':

						#適正値は数字*100だが、それだと結構テンポ悪いので
						line = 'wait ' + str(convert_list[0] * 20) + '\n'

					#JUMP_UNLESS 飛び先指定(select直後)
					elif last_hash == 'JUMP_UNLESS':
						line = (r'mov %select_cnt,%select_var' + '\n')
						line+= (r'if %select_cnt==0 goto *JUMP_' + str(convert_list[0]) + '_' + str(p.stem).replace('.', '_') + '\n')
						line+= (r'if %select_cnt!=0 sub %select_cnt,1' + '\n')
					
					#JUMP 飛び先指定					
					elif last_hash == 'JUMP':
						line = (r'if %select_cnt==0 goto *JUMP_' + str(convert_list[0]) + '_' + str(p.stem).replace('.', '_') + '\n')
						line+= (r'if %select_cnt!=0 sub %select_cnt,1' + '\n')

					#READ_SCENARIO gosub的な
					elif last_hash == 'READ_SCENARIO':
						line = ('gosub *SCR_' + str(convert_list[1]) + '_gsc\n' )

					#15 select前画像決定部分
					elif last_hash == '15':
						line = ('mov %21,' + str(convert_list[2]) + ':mov %22,' + str(convert_list[3]) + ':mov %23,' + str(convert_list[4]) + '\n')

					#IMAGE_GET grpe 背景
					elif last_hash == 'IMAGE_GET':
						line = ('RSC_IMAGE_GET ' + str(convert_list[0]) + '\n')

					#SPRITE grpo_bu 立ち絵？
					elif last_hash == 'SPRITE':
						line = ('RSC_SPRITE ' + str(convert_list[2]) + '\n')

					#60 BGM？
					elif last_hash == '60':
						line = ('RSC_BGM ' + str(convert_list[0]) + '\n')

					#62 効果音？
					elif last_hash == '62':
						line = ('RSC_SE ' + str(convert_list[0]) + '\n')

					#36 スプライト除去
					elif last_hash == '36':
						line = ('csp -1' + '\n')

					# (多分)暗転
					elif last_hash == '21':
						line = ('bg black,10\n')

					#61 BGMのフェードアウト
					elif last_hash == '61':
						line = ('bgmfadeout 1000\n')						

					#65 動画？
					elif last_hash == '65':
						line = ('RSC_MOVIE ' + str(convert_list[0]) + ',' + str(movie_cnt) +'\n')
						movie_cnt += 1

					#多分無視して良いと思われる命令のみなさん！！！！！！！！レスキュー開始！！！！
					elif last_hash in [
							'6144',#場面ごとのセーブ時サムネイル切り替えに使われているもよう
							'BLEND_IMG',#画像周りなんだろうけどNSCに対応する命令が見つからない
							'CLEAR_MESSAGE_WINDOW',#このコンバータ毎回画面クリアしてるんで...
						]:
						line = (';' + line) if DEBUG_MODE else ''

					#その他 - 知らんのでprint出す
					else:
						if DEBUG_MODE:
							print('UnknownCMD:' + last_hash)
						line = (';' + line) if DEBUG_MODE else ''

					#処理終了後"last_hash"をもどす
					last_hash = False
				
				#その他 - エラー防止の為コメントアウト
				else:

					#ルビをNSC形式へ置換
					line = re.sub(r'\|(.+?)\[(.+?)?\]', r'(\1/\2)', line)
					line = re.sub(r'(.)\[(.+?)?\]', r'(\1/\2)', line)

					#原作のdelayらしきものを抹消(実装面倒なので)
					line = re.sub(r'\^d([0-9]+)', '', line)
					line = line.replace(r'^', '')

					#ここ半角英数字の入ったシナリオ文へのごまかし - kagerou専用
					line = line.replace(r'!', r'！')
					line = line.replace(r'?', r'？')
					line = line.replace(r'essence', r'ｅｓｓｅｎｃｅ')

					#半角英数字が入ってる場合 - シナリオ文ではないと判定
					if re.search(r'[A-z0-9]', line):
						print('UnknownSTR:' + line.replace('\n', ''))
						line = (';' + line) if DEBUG_MODE else ''
						
					#半角英数字が入ってない場合 - シナリオ文です
					else:
						line_message = True
						mes_cnt += 1
				
				#シナリオ文終了時
				if (not line_message) and (last_message):
					#改ページ
					line = ('\\\n' + line)

					#行数カウント 最大数の場合代入
					if (mes_cnt > mes_max):
						mes_max = mes_cnt
					
					#行数カウント 初期化
					mes_cnt = 0

				txt += line

			#デコード済みtxt一つごとに終了時return
			txt += '\nreturn'

	#ガ バ ガ バ 修 正
	txt = txt.replace(r'gosub *SCR_1000_gsc', r'gosub *SCR_0999_gsc:gosub *SCR_1000_gsc')#"はじめから"時の最初の「～遍く活字愛好家に捧ぐ～」に飛ばす
	txt = txt.replace(r'gosub *SCR_1132_gsc', r'gosub *SCR_1132_gsc:return')#個別ルート終了時次の個別ルートにそのまま飛ぶのを防ぐ
	txt = txt.replace(r'gosub *SCR_1134_gsc', r'gosub *SCR_1134_gsc:return')#同上
	txt = txt.replace(r'gosub *SCR_1240_gsc', r'gosub *SCR_1240_gsc:return')#同上
	txt = txt.replace(r'gosub *SCR_1242_gsc', r'gosub *SCR_1242_gsc:return')#同上
	txt = txt.replace(r'gosub *SCR_1016_gsc', r'gosub *SCR_1016_gsc:RSC_select_chara2')
	txt = txt.replace(r'渡し守にそう問いかけられて、築宮の中に咄嗟に浮かんだのは―――', r'渡し守にそう問いかけられて、築宮の中に咄嗟に浮かんだのは―――' + '\\\ngoto *skip_fix1')#個別ルート分岐ごまかし1
	txt = txt.replace(r'mov %21,8061:mov %22,8062:mov %23,8063', '*skip_fix1\n' + r'mov %21,8061:mov %22,8062:mov %23,8063:RSC_select:RSC_select_chara')#個別ルート分岐ごまかし2

	#出力結果を書き込み
	open(zero_txt, 'w', errors='ignore').write(txt)

	#デバッグ時のみ最大行数を表示
	if DEBUG_MODE:
		print('最大行数:' + str(mes_max))

	return


def junk_del(delete_list):

	#リスト内のディレクトリパスでfor
	for d in delete_list:

		#ディレクトリパス内のファイル一覧でfor
		for p in d.glob('*'):

			#削除
			p.unlink()
		
		#ディレクトリも削除
		d.rmdir()

	return


# メイン関数
def main(debug):

	#同一階層のパスを変数へ代入
	same_hierarchy = Path.cwd()

	#debug時にtestフォルダに入れないやつ(default.txt等)はこっちを利用
	same_hierarchy_const = same_hierarchy

	if debug:
		#デバッグ時はtestディレクトリ直下
		same_hierarchy = (same_hierarchy / 'test')

	#利用するパスを辞書に入れ一括代入
	PATH_DICT = {
		#先に準備しておくべきファイル一覧 - kagerou専用
		'bgm'    :(same_hierarchy / 'bgm'),
		'grpe'   :(same_hierarchy / 'grpe'),
		'grpo'   :(same_hierarchy / 'grpo'),
		'grpo_bu':(same_hierarchy / 'grpo_bu'),
		'grps'   :(same_hierarchy / 'grps'),
		'scr'    :(same_hierarchy / 'scr'),
		'voice'  :(same_hierarchy / 'voice'),
		'wav'    :(same_hierarchy / 'wav'),
		'mov'    :(same_hierarchy / 'mov'),

		'gsc_exe':(same_hierarchy_const / 'gscScriptCompAndDecompiler.exe'),
		'default':(same_hierarchy_const / 'default.txt'),
	}

	PATH_DICT2 = {
		#変換後に出力されるファイル一覧
		'scr_dec':(same_hierarchy / 'scr_dec'),
		'0_txt'  :(same_hierarchy / '0.txt'),
	}

	#ディレクトリの存在チェック
	dir_check_result = dir_check(PATH_DICT.values())

	#存在しない場合終了
	if not dir_check_result:
		return

	#シナリオを平文にデコードする
	text_dec(PATH_DICT['gsc_exe'], PATH_DICT['scr'], PATH_DICT2['scr_dec'] )

	#GARBroでぶっこ抜いたogg何故かONSで使えないのでデコード
	sound_dec([
		PATH_DICT['bgm'],
		PATH_DICT['wav'],
		PATH_DICT['voice'],
	])

	#txt置換→0.txt出力
	text_cnv(PATH_DICT['default'], PATH_DICT2['0_txt'], PATH_DICT2['scr_dec'], PATH_DICT.keys())

	#不要データ削除
	junk_del([
		PATH_DICT['scr'], 
		PATH_DICT2['scr_dec'],
	])


main(DEBUG_MODE)