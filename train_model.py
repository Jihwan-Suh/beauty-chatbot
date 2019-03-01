import pandas as pd
import numpy as np
from numpy.random import RandomState
import itertools # 하이퍼 파라미터를 구하기 위해 반복적으로 값을 불러오는 기능을 가지고 있습니다. 
from scipy import sparse
from lightfm import LightFM #헤비유저 추천에 사용할 모델입니다.
from lightfm.evaluation import auc_score
from lightfm.cross_validation import random_train_test_split
import sqlite3
import pickle


def sample_hyperparameters():
	"""
	Randomized search를 이용한 하이퍼 파라미터를 구하기 위한 함수
	"""
	np.random.seed(523)# 데이터가 변할 때를 제외하고 항상 일정한 파라미터가 나오도록 하기위해 설정합니다.

	while True:
		yield {
			"no_components": np.random.randint(16, 64),
			"learning_schedule": np.random.choice(["adagrad", "adadelta"]),
			"loss": np.random.choice(["bpr", "warp", "warp-kos"]),
			"learning_rate": np.random.exponential(0.05),
			"item_alpha": np.random.exponential(1e-8),
			"user_alpha": np.random.exponential(1e-8),
			"max_sampled": np.random.randint(5, 15),
			"num_epochs": np.random.randint(5, 100),
		}

def runMF(product_type, num_samples=20, num_threads=2):
	"""

	헤비유저를 위한 화장품 추천 모델을 만들기 위한 함수입니다.
	LightFM 모델을 사용합니다.
	sample_hyperparameters 함수를 이용하여 하이퍼 파라미터를 구해서 모델 파라미터에 적용시켜 모델을 만들어 줍니다.
	
	-------
	
	interactions:유저와 화장품 정보로 만든 희소 행렬 
	num_samples: 하이퍼 파라미터를 구할때 만들어지는 랜덤한 숫자들을 지정한 개수만큼만 나오게 합니다
		
	"""
	interactions=pickle.load(open("./pickle_data/"+product_type+"/interactions.p", "rb"))
	user_features=pickle.load(open("./pickle_data/user_features.p", "rb"))
	
	x = sparse.csr_matrix(interactions.values)

	train, test = random_train_test_split(x, test_percentage=0.2, random_state=RandomState(523))

	#itertools 패키지의 islice기능을 사용하여 위에서 설정한 파라미터값을 설정한 num_samples값만큼 반복적으로 나오게하여 적용합니다.
	for hyperparams in itertools.islice(sample_hyperparameters(), num_samples):
		num_epochs = hyperparams.pop("num_epochs")

		model = LightFM(**hyperparams)
		model.fit(train, user_features, epochs=num_epochs, num_threads=num_threads, verbose=True)

		auc = auc_score(model, test, train_interactions = train, num_threads=num_threads,user_features=user_features).mean()

		hyperparams["num_epochs"] = num_epochs

		yield (auc, model)

def save_best_model(product_type):
	(auc_score, model) = max(runMF(product_type), key=lambda x: x[0])
	pickle.dump(model, open("./pickle_data/"+product_type+"/model.p", "wb"))


def recommendation_user(user_id, product_type, threshold = 0, nrec_items = 5, show = False):
    '''
    유저에게 추천화장품을 제공해주기 위한 기능입니다. 
    요구되는 입력 값 - 
        - model = 훈련시켜 만든 모델
        - interactions = 모델을 훈력시키는데 사용한 데이터
        - user_id = 추천을 받으려는 유저 ID
        - user_dict = 유저 정보를 담고있는 유저 딕셔너리 
        - item_dict = 화장품 id와 화장품 이름을 가지고 있는 딕셔너리
        - threshold = interaction matrix안에서 임계 값보다 높은 값을 나오게 합니다.
        - nrec_items = 추천 화장품 개수
    기대되는 결과 값 - 
        - 이미 알고 있는 화장품 리스트
        - 유저에게 추천해 줄 화장품 리스트
    '''
    model=pickle.load(open("./pickle_data/"+product_type+"/model.p", "rb"))
    interactions=pickle.load(open("./pickle_data/"+product_type+"/interactions.p", "rb"))
    user_features=pickle.load(open("./pickle_data/user_features.p", "rb"))
    user_dict=pickle.load(open("./pickle_data/"+product_type+"/user_dict.p", "rb"))
    item_dict=pickle.load(open("./pickle_data/"+product_type+"/item_dict.p", "rb"))

    n_users, n_items = interactions.shape
    user_x = user_dict[user_id]

    scores = pd.Series(model.predict(user_x,np.arange(n_items), user_features=user_features))
    scores.index = interactions.columns
    scores = list(pd.Series(scores.sort_values(ascending=False).index))
    
    known_items = list(pd.Series(interactions.loc[user_id,:] \
                                 [interactions.loc[user_id,:] > threshold].index) \
								 .sort_values(ascending=False))
    
    scores = [x for x in scores if x not in known_items]
    return_score_list = scores[0:nrec_items]
    known_items = list(pd.Series(known_items).apply(lambda x: item_dict[x]))
    scores = list(pd.Series(return_score_list).apply(lambda x: item_dict[x]))
	
    if show == True:
        print("Known Likes:")
        counter = 1
        for i in known_items:
            print(str(counter) + '- ' + i)
            counter+=1

        print("\n Recommended Items:")
        counter = 1
        for i in scores:
            print(str(counter) + '- ' + i)
            counter+=1
    return return_score_list

if __name__=="__main__":
	db_path=
	conn=sqlite3.connect(db_path)
	c=conn.cursor()
	rows=c.execute("SELECT DISTINCT product_type FROM products")
	types=rows.fetchall()
	c.close()

	for ptype in types:
		save_best_model(ptype[0])
