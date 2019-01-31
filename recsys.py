import pandas as pd
import numpy as np
import itertools # 하이퍼 파라미터를 구하기 위해 반복적으로 값을 불러오는 기능을 가지고 있습니다. 
from scipy import sparse
from lightfm import LightFM #헤비유저 추천에 사용할 모델입니다.
from sklearn.metrics.pairwise import cosine_similarity 

def create_interaction_matrix(df,user_col, item_col, rating_col, norm= False, threshold = None):
    '''
    데이터 프레임 형태의 interation 행렬 데이터를 만들기 위한 기능입니다.
    요구되는 입력 값 -
        - df =  유저와 화장품의 상호관계를 포함한 Pandas DataFrame 
        - user_col = 유저의 고유 정보를 포함한 column name
        - item_col = 화장품 고유 정보를 포함한 column name 
        - rating col = 유저가 화장품에 대해 평가한 점수를 가진 column name
        - norm (optional) = 정규화된 rating 점수가 필요하다면 True로 적습니다.
        - threshold (norm을 True로 설정한 경우) = 임계 값보다 높은 값을 나오게 합니다.
    기대되는 결과 값 - 
        - 추천 알고리즘에 적용시키는데 알맞은 유저와 화장품 정보를 행과 열로 가지고 있는 매트릭스 형태의 DataFrame
    '''
    #유저 아이디와 화장품 아이디를 행과 열값으로 가지고 그에 대응하는 평점 정보를 가지고 있는 interactions 변수를 만듭니다. 
    interactions = df.groupby([user_col, item_col])[rating_col] \
            .sum().unstack().reset_index(). \
            fillna(0).set_index(user_col)
    if norm:
        interactions = interactions.applymap(lambda x: 1 if x > threshold else 0)
    return interactions

def create_user_dict(interactions):
    '''
    interation dataset의 index와 번호를 이용해서 유저 딕셔너리를 만들기 위한 기능입니다.
    요구되는 입력 값 - 
        interactions - create_interaction_matrix 함수를 이용해 만든 dataset
    기대되는 결과 값 -
        user_dict - 유저 인덱스와 유저 아이디를 포함하고 있는 딕셔너리 형태의 결과값
    '''
    user_id = list(interactions.index)
    user_dict = {}
    counter = 0 
    for i in user_id:
        user_dict[i] = counter
        counter += 1
    return user_dict
    
def create_item_dict(df,id_col,name_col):
    '''
    화장품 id와 화장품 이름을 기반으로 아이템 딕셔너리를 만들기 위한 기능
    요구되는 입력 값 - 
        - df =  유저와 화장품의 상호관계를 포함한 Pandas DataFrame 
        - id_col = 화장품 고유 id를 포함한 Column name
        - name_col = 화장품의 이름을 포함한 Column name 
    기대되는 결과 값 -
        item_dict = 화장품 id와 화장품 명을 포함한 딕셔너리 형태
    '''
    item_dict ={}
    for i in range(df.shape[0]):
        item_dict[(df.loc[i,id_col])] = df.loc[i,name_col]
    return item_dict

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
            "num_epochs": np.random.randint(5, 50),
        }

        
def runMF(interactions, num_samples=10, num_threads=1):
    """
   
    헤비유저를 위한 화장품 추천 모델을 만들기 위한 함수입니다.
    LightFM 모델을 사용합니다.
    sample_hyperparameters 함수를 이용하여 하이퍼 파라미터를 구해서 모델 파라미터에 적용시켜 모델을 만들어 줍니다.
    
    -------
    
    interactions:유저와 화장품 정보로 만든 희소 행렬 
    num_samples: 하이퍼 파라미터를 구할때 만들어지는 랜덤한 숫자들을 지정한 개수만큼만 나오게 합니다
        

    """
    #itertools 패키지의 islice기능을 사용하여 위에서 설정한 파라미터값을 설정한 num_samples값만큼 반복적으로 나오게하여 적용합니다.
    for hyperparams in itertools.islice(sample_hyperparameters(), num_samples):
        num_epochs = hyperparams.pop("num_epochs")
        x = sparse.csr_matrix(interactions.values)

        model = LightFM(**hyperparams)
        model.fit(x, epochs=num_epochs, num_threads=num_threads)

        hyperparams["num_epochs"] = num_epochs

        return model

def sample_recommendation_user(model, interactions, user_id, user_dict, 
                               item_dict,threshold = 0,nrec_items = 10, show = True):
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
    
    n_users, n_items = interactions.shape
    # user_dict에서 user_id를 가져옵니다.
    user_x = user_dict[user_id]
    #만든 모델을 이용하여 user_x의 predict값을 구해줍니다.
    scores = pd.Series(model.predict(user_x,np.arange(n_items)))
    #예측한 series형태의 인덱스값에 interations의 열 값을 넣어줍니다.
    scores.index = interactions.columns
    #scores 값을 내림차순으로 정렬해 줍니다.
    scores = list(pd.Series(scores.sort_values(ascending=False).index))
    #known_items를 interations의 user_id를 이용해 구해줍니다.
    known_items = list(pd.Series(interactions.loc[user_id,:] \
                                 [interactions.loc[user_id,:] > threshold].index) \
                         .sort_values(ascending=False))
    
    scores = [x for x in scores if x not in known_items]
    #nrec_items 설정한 개수만큼 화장품을 추천해 줍니다.
    return_score_list = scores[0:nrec_items]
    known_items = list(pd.Series(known_items).apply(lambda x: item_dict[x]))
    scores = list(pd.Series(return_score_list).apply(lambda x: item_dict[x]))
    # if show == True:
    #     print("Known Likes:")
    #     counter = 1
    #     for i in known_items:
    #         print(str(counter) + '- ' + i)
    #         counter+=1

    #     print("\n Recommended Items:")
    #     counter = 1
    #     for i in scores:
    #         print(str(counter) + '- ' + i)
    #         counter+=1
    return return_score_list