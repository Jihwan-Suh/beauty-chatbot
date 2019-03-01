import pandas as pd
import numpy as np
from scipy import sparse
import sqlite3
import pickle

#추천 모델 훈련과 작동에 관한 데이터를 전처리하고 저장한다.
def create_basic_dict(db_path):
    """
    입력 값
    - db_path: db저장소 위치, 원본 데이터를 끌어와서 전처리 하는데 쓰인다.

    출력 값
    - rating_dict: 상품 종류별 데이터 프레임을 담고 있는 딕셔너리

    """
    #db로부터 데이터를 불러온다.
    conn=sqlite3.connect(db_path)
    c=conn.cursor()

    #제품 종류를 가져온다.
    ptype = c.execute("Select Distinct product_type From products")
    ptypes = ptype.fetchall()

    #user 테이블을 참고하여 필요한 데이터를 불러온다.
    users=c.execute("Select user_id, user_name From users")
    users=users.fetchall()
    users=pd.DataFrame(columns=["user_id", "user_name"], data=users).copy()

    rating_dict={}
    #제품 정보별로 순회하며 새로운 rating 형식을 만든다. 모든 유저의 제품별 rating 프레임을 만든다. 구매 내역이 있으면 해당 레이팅이 없으면 0이 들어간다.
    for product_type in ptypes:
        #레이팅 정보를 불러온다.
        ratings=c.execute("Select * From ratings Where product_id in (Select product_id From products Where product_type=?)",(str(product_type[0]),))
        ratings=ratings.fetchall()
        ratings=pd.DataFrame(columns=["user_id", "product_id", "rating"] ,data=ratings).copy()

        #모든 제품 정보를 불러온다.
        products= c.execute("Select product_id, brand_name, product_name, product_price From products Where product_type=?",(str(product_type[0]),))
        products=products.fetchall()
        products=pd.DataFrame(columns=["product_id", "brand_name", "product_name", "product_price"], data=products).copy()

        #새로운 레이팅 프레임을 만든다.
        temp_df=users[['user_id']]
        temp_df=pd.merge(temp_df, ratings, how='left')
        ratings=temp_df
        temp_value={"product_id": 999999, "rating": 0}
        ratings=ratings.fillna(temp_value)

        rating_dict[product_type[0]]=ratings

    return rating_dict



def create_interaction_matrix(df, user_col, item_col, rating_col, norm= True, threshold = 3):
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
    interactions = df.groupby([user_col, item_col])[rating_col].sum().unstack().reset_index().fillna(0).set_index(user_col)
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



def create_user_features(db_path):
    '''
    csr matrix 형태의 데이터를 만들기 위한 기능입니다.
    요구되는 입력 값 -
        - df =  유저의 특성이 카테고리 형태로 되어있어 pd.get_dummies()가 적용 가능한 데이터 프레임
    결과 값-
        - user_csr = 유저의 특성을 더미 변수화시킨 csr_matrix  
    '''
    #db로부터 데이터를 불러온다.
    conn=sqlite3.connect(db_path)
    c=conn.cursor()

    #user 테이블을 참고하여 필요한 데이터를 불러온다.
    users=c.execute("Select user_id, user_name, age, skin_type From users")
    users=users.fetchall()
    users=pd.DataFrame(columns=["user_id", "user_name", "age", "skin_type"], data=users).copy()

    #유저 연령대를 설정한다.
    users["age_range"]=users["age"].apply(lambda x: "10대" if x>=10 and x<20 else "20대 초반" \
                                      if x>=20 and x<25 else "20대 후반" if x>=24 and x<30 else "30대 초반"\
                                      if x>=30 and x<35 else "30대 후반 이상").copy()

    #원하는 피처를 더미화 시킨다.
    users_feat = users.merge(pd.get_dummies(users.age_range, prefix='age_range'), left_index=True, right_index=True)
    users_feat = users_feat.merge(pd.get_dummies(users.skin_type, prefix='skin_type'), left_index=True, right_index=True)

    #csr_matrix를 만들기 위한 작업
    users_feat.drop(["age","skin_type","age_range"], axis=1, inplace=True)

    u=users_feat.pivot_table(index=['user_id'])

    user_csr=sparse.csr_matrix(u,dtype='f')

    c.close()

    return user_csr



# def create_item_features(db_path):
#     '''
#     csr matrix 형태의 데이터를 만들기 위한 기능입니다.
#     요구되는 입력 값 -
#         - df =  제품의 특성이 카테고리 형태로 되어있어 pd.get_dummies()가 적용 가능한 데이터 프레임
#     결과 값-
#         - item_csr = 유저의 특성을 더미 변수화시킨 csr_matrix  
#     '''
#     #db로부터 데이터를 불러온다.
#     conn=sqlite3.connect(db_path)
#     c=conn.cursor()

#     products= c.execute("Select product_id, brand_name, product_name, product_price From products Where product_type=?",(str(product_type),))
#     products=products.fetchall()
#     products=pd.DataFrame(columns=["product_id", "brand_name", "product_name", "product_price"], data=products).copy()

#     #가격 범주화를 위한 사전 작업 실시
#     products['product_price']=products['product_price'].replace(',','',regex=True)
#     products['product_price']=products['product_price'].replace('원','',regex=True).astype(float) 
    
#     # 가격대 변경
#     products.loc[(products['product_price']<18000), 'price'] = '저가'
#     products.loc[(products['product_price']>=18000) & (products['product_price'] <27000), 'price'] = '중저가'
#     products.loc[(products['product_price']>=27000) & (products['product_price'] <39000), 'price'] = '중고가'
#     products.loc[(products['product_price']>=39000) , 'price'] = '고가'

#     # 원하는 columns만 가져온다.
#     new_products=products[['product_name','brand_name','price']].copy()

#     # 브랜드명과 가격 더미화
#     product_features = new_products.merge(pd.get_dummies(new_products.brand_name, prefix='brand_name'), left_index=True, right_index=True)
#     product_features = product_features.merge(pd.get_dummies(new_products.price, prefix='price'), left_index=True, right_index=True)

#     product_features.drop(["brand_name","price"], axis=1, inplace=True)
    
#     # 화장품 명을 인덱스로 하는 행렬 생성
#     p = product_features.set_index("product_name")
#     item_csr=sparse.csr_matrix(p,dtype='f')

#     return item_csr

#lightfm에서 필요로하는 데이터를 만들어준다. interaction_matrix, weight_matrix 그리고 user_features, item_features를 만들어준다.
def create_require_data(rating_dict, db_path):
    for key in rating_dict.keys():
        conn=sqlite3.connect(db_path)
        c=conn.cursor()
        rows=c.execute("SELECT product_id, product_name FROM products WHERE product_type=?",(str(key),))
        rows=rows.fetchall()
        c.close()

        products=pd.DataFrame(columns=["product_id", "product_name"] ,data=rows).copy()
        
        interactions_matrix = create_interaction_matrix(rating_dict[key],"user_id", "product_id", "rating")
        user_dict=create_user_dict(interactions_matrix)
        item_dict=create_item_dict(products,"product_id", "product_name")

        # 필요 데이터를 저장한다.
        pickle.dump(interactions_matrix, open("./pickle_data/"+key+"/interactions.p", "wb"))
        pickle.dump(user_dict, open("./pickle_data/"+key+"/user_dict.p", "wb"))        
        pickle.dump(item_dict, open("./pickle_data/"+key+"/item_dict.p", "wb"))

        print(interactions_matrix.shape)
    user_features=create_user_features(db_path)
    pickle.dump(user_features, open("./pickle_data/user_features.p", "wb"))


if __name__=="__main__":
    db_path="./glow_db.sqlite3"

    rating_dict=create_basic_dict(db_path)

    create_require_data(rating_dict, db_path)
