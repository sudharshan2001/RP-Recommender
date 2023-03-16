import streamlit as st
import cohere
import numpy as np
import pandas as pd
from qdrant_client.http import models
# import warnings
# warnings.filterwarnings('ignore')
import qdrant_client
import easynmt
from config import CONFIG

model_translation = easynmt.EasyNMT('m2m_100_418M')# mbart50_en2m

model_type = "small"

cohere_api_key = CONFIG.COHERE_API_KEY
QDRANT_URL = CONFIG.QDRANT_URL
QDRANT_API_KEY = CONFIG.QDRANT_API_KEY

ds = pd.read_csv('data/dataarxivfinal.csv')
print(ds.shape)
cohere_client = cohere.Client(api_key=cohere_api_key)
embeddings = np.load("embedding_model.npy")
collection_name = "my_collection"
distance = models.Distance.COSINE

client = qdrant_client.QdrantClient(
    url= QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

# Create Qdrant collection and upload the Embeddings
button_for_upload = st.sidebar.button('Load')
if button_for_upload:
    
    with st.spinner("Loading Models"):
        collection_id = client.recreate_collection(collection_name = collection_name,
                                            vectors_config= models.VectorParams(size=embeddings.shape[1], distance=distance))


        vectors=[list(map(float, vector)) for vector in embeddings]

        ids = []
        for i, j in enumerate(embeddings):
            ids.append(i)

        client.upload_collection(
            collection_name=collection_name, 
            ids=ids,
            vectors=vectors,
            batch_size=128
            )

article_rec_type = st.sidebar.selectbox(
    "Recommend article type by",
    ( "Article Name", "Article Content", "Article Translator", "Article Summarizer")
)

def article_summarizer():
    col1, col2 = st.columns(2)
    summarize_decision  = st.button('Summarize')

    with col1:
        with st.expander("Input text"):
            prompt = st.text_area("Paste the sentence that needs to be Summarized")

    with col2:
        with st.expander("Summarized texts"):
            if summarize_decision:
                response = cohere_client.generate( 
                                    model='xlarge', 
                                    prompt = prompt,
                                    max_tokens=512, 
                                    temperature=0.6, 
                                    k=0, 
                                    p=1, 
                                    frequency_penalty=0, 
                                    presence_penalty=0, 
                                    stop_sequences=["--"],truncate="end"
                                    )

                summary = response.generations[0].text
                st.write(summary)

language_dict =  {"Tamil":"ta", "Nepali":"ne", "Indonesian":"id", "Thai":"th","Spanish":"es", "Russian":"ru", "Turkish":"tr", "French":"fr"}
def article_translator():
    col1, col2 = st.columns(2)
    
    language = st.sidebar.selectbox(
    "Select Language",
    ( "Tamil", "Nepali", "Indonesian", "Thai","Spanish", "Russian", "Turkish", "French")
    )

    translate_decision  = st.button('Translate')
    with col1:
        with st.expander("Input text"):
            text = st.text_area("Paste the sentence that needs to be Translated")

    with col2:
        with st.expander("Translated text"):
            if translate_decision:
                result = model_translation.translate(text, target_lang=language_dict[language])
                st.write(result)


def article_name():
    title = st.selectbox('Article Name', options=tuple(ds['title'].values))
    top_k = st.slider("Number of recommendations", 1, 10, step=1)
    button = st.button('Predict')

    if button:

        query_to_ = ds[ds['title']==title].head(1)['abstract'].values[0]
        query_vector = cohere_client.embed([query_to_], model=model_type, truncate="RIGHT").embeddings[0]
        query_vector = list(map(float, query_vector))
        search_result = client.search(collection_name=collection_name, query_vector=query_vector,limit=top_k)
        similar_text_indices = [hit.id for hit in search_result]

        score_ =  [record.score for record in search_result]

        for j,i in enumerate(ds.iloc[similar_text_indices].iterrows()):
            st.write(f"**{i[1]['title']}** score:{score_[j]}")
 
def article_content():
    search_decision  = st.button('Search')

    with st.expander("Input text"):
        query_to_ = st.text_area("Paste the Contents that need to be searched for")
        top_k = st.slider("Number of recommendations", 1, 10, step=1)

    if search_decision:
        query_vector = cohere_client.embed([query_to_], model=model_type, truncate="RIGHT").embeddings[0]
        query_vector = list(map(float, query_vector))
        search_result = client.search(collection_name=collection_name, query_vector=query_vector,limit=top_k)
        similar_text_indices = [hit.id for hit in search_result]

        score_ =  [record.score for record in search_result]

        for j,i in enumerate(ds.iloc[similar_text_indices].iterrows()):
            st.write(f"**{i[1]['title']}** score:{score_[j]}")
            

if article_rec_type=='Article Name':
    article_name()
elif article_rec_type == 'Article Translator':
    article_translator()
elif article_rec_type == "Article Summarizer":
    article_summarizer()
else:
    article_content()