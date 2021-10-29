import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import locale
#htm5lib
import io
import math
import plotly.graph_objects as go
import plotly.express as px

locale.setlocale(locale.LC_TIME, 'es_ES')# this sets the date time formats to es_ES
st.set_page_config(page_title='Cierre de centrales de cobre',layout="wide")

def buscar_enlace():
        # concretar la pagina donde se localiza el archivo
        url='https://www.cnmc.es/ambitos-de-actuacion/telecomunicaciones/concrecion-desarrollo-obligaciones'
        # el user-agent de requests nos da error 403 Forbidden por defecto, configuramos un user-agent
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
        r = requests.get(url, headers=headers)
        # extraemos el contenido html de la pagina
        soup = BeautifulSoup(r.text, features="html.parser")
        # filtramos por las divisiones de clase well (contienen los recuadros con acceso a archivos)
        windows = soup.find_all("div",{"class":"well"})

        # para encontrar el href archivo correspondiente siempre se nota la notación y la palabra cierre es unica
        urlcentral=[]
        for window in windows:
                items = window.find_all("a", href=True)
                urlcentral= urlcentral+[item.attrs['href'] for item in items if "cierre" in item.attrs['href']]
        # vemos que hay dos archivos de centrales, cogemos el primero, el segundo corresponde al utilizado para el
        # modelo de costes, que se encuentra dispuesto debajo del apartado de cierre. Añadimos cabecera de la web
        urlcentral='https://www.cnmc.es'+urlcentral[0]
        return urlcentral

@st.cache(allow_output_mutation=True)
def cargar_csv(urlcentral):
        # el user-agent de requests nos da error 403 Forbidden por defecto, configuramos un user-agent
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
        # El archivo también se encuentra con error 403 Forbidden al acceder, especificamos el mismo user-agent
        response = requests.get(urlcentral,headers=headers)
        # io nos permite convertir la tabla es un file_object valido para la función read_csv. Decode nos permite
        # decode iso-8859-1 nos permite decodificar todos los bytes del archivo, incluido tildes.
        file_object = io.StringIO(response.content.decode('iso-8859-1'))
        # Leemos el archivo en pandas, en este caso el separador es ; como es habitual en archivos ES
        c=pd.read_csv(file_object, sep=';')
        # Convertimos en datetime las columnas de fechas, por defecto python identifica MM/DD/AA por lo que concretamos
        # el formato
        c['Fin garantía']=pd.to_datetime(c['Fin garantía'], format='%d/%m/%Y')
        c['Cierre definitivo']=pd.to_datetime(c['Cierre definitivo'], format='%d/%m/%Y')
        return c

@st.cache(allow_output_mutation=True)
def tab_cautonoma():
        df =pd.read_csv('provincia.csv',sep=';')
        return df

def estado_central(df):
        if df['Cierre definitivo'] <= datetime.now():
                return 'CERRADA'
        elif df['Fin garantía'] <= datetime.now():
                return 'FIN GARANTÍA'
        else:
                return 'FECHA PROGRAMADA'

def add_cautonoma_estado(df):
        df['CODIGOPROV'] = df['Código MIGA'].apply(lambda x: math.floor(x/100000)).astype('int64')
        cautonoma = tab_cautonoma()
        df = pd.merge(df, cautonoma[['CODIGOPROV','CAUTONOMA']], on='CODIGOPROV')
        df['ESTADO'] = df.apply(estado_central, axis=1)
        return df

@st.cache(allow_output_mutation=True)
def set_value(rec,code):
        try:
                val=int(rec[rec['ESTADO'] == code]['CENTRAL'])
        except:
                val=0
        return val

urlcentral = buscar_enlace()
dfcierre = cargar_csv(urlcentral)
dfcierre = add_cautonoma_estado(dfcierre)

st.title('Proceso de cierre de centrales de cobre')

st.sidebar.header('Menú')
menu=st.sidebar.radio('Escoge una opción',('Datos Nacionales','Datos por Comunidad Autónoma','Datos por Provincia','Buscador de Central','Acerca de'))

def indicadores_generales(df, rec):
        st.subheader('Indicadores Generales')
        fig = go.Figure()
        fig.add_trace(go.Indicator(
                mode="number",
                value=int(df['Cierre definitivo'].count()),
                title={'text': 'Centrales notificadas'},
                domain={'row': 0, 'y': [0, 1]}))

        fig.add_trace(go.Indicator(
                mode="number",
                value=set_value(rec,"FECHA PROGRAMADA"),
                title={'text': 'Con fecha programada '},
                domain={'row': 0, 'column': 1}))

        fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=set_value(rec,"FECHA PROGRAMADA") / int(df['Cierre definitivo'].count()) * 100,
                number={'suffix': "%"},
                domain={'row': 1, 'column': 1},
                gauge={'axis': {'range': [0, 100]}}))

        fig.add_trace(go.Indicator(
                mode="number",
                value=set_value(rec,"FIN GARANTÍA"),
                title={'text': 'En fin de garantía'},
                domain={'row': 0, 'column': 2}))

        fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=set_value(rec,"FIN GARANTÍA")/ int(df['Cierre definitivo'].count()) * 100,
                number={'suffix': "%"},
                domain={'row': 1, 'column': 2},
                gauge={'axis': {'range': [0, 100]}}))

        fig.add_trace(go.Indicator(
                mode="number",
                value=set_value(rec,"CERRADA"),
                title={'text': 'Cerradas definitivamente'},
                domain={'row': 0, 'column': 3}))

        fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=set_value(rec,"CERRADA") / int(df['Cierre definitivo'].count()) * 100,
                number={'suffix': "%"},
                domain={'row': 1, 'column': 3},
                gauge={'axis': {'range': [0, 100]}}))

        fig.update_layout(grid={'rows': 2, 'columns': 4, 'pattern': "independent"})
        st.plotly_chart(fig, use_container_width=True)

@st.cache
def convert_df(df):
        return df.to_csv(sep=';').encode('iso-8859-1')

def grafica(df,mode):
        st.subheader('Centrales de cobre en cierre por '+mode+' y estado de cierre')
        recg = df[['ESTADO', mode, 'CENTRAL']].groupby(['ESTADO', mode]).count().fillna(
                0).reset_index()
        fig = px.bar(recg, x=mode, y="CENTRAL", color="ESTADO",
                     category_orders={"ESTADO": ['CERRADA', 'FIN GARANTÍA', 'FECHA PROGRAMADA']},
                     title='Centrales de cobre en cierre por '+mode+' y estado de cierre')
        fig.update_xaxes(categoryorder='total descending')
        fig.update_layout(height=700)
        st.plotly_chart(fig, use_container_width=True)
        expander = st.expander('Ver y descargar tabla resumen')
        recg_pivot = pd.pivot_table(recg, index=mode, columns='ESTADO', values='CENTRAL', fill_value=0,
                                      aggfunc=sum, margins=True)
        expander.table(recg_pivot)
        expander.download_button('Descargar tabla en csv', data=convert_df(recg_pivot), file_name='res_'+mode+'.csv',
                                      mime='text/csv')

def cierretemporal(dfevo,dfcum,word):
        st.subheader('Cierre de centrales por año en '+word)
        fig = px.bar(dfevo, x='Cierre definitivo', y="CENTRAL", color="ESTADO",
                     category_orders={"ESTADO": ['CERRADA', 'FIN GARANTÍA', 'FECHA PROGRAMADA']},
                     title='Cierre de centrales por año en '+word)
        fig.update_xaxes(categoryorder='total descending')
        fig.update_layout(height=700)
        st.plotly_chart(fig, use_container_width=True)

        expander = st.expander('Ver y descargar tabla resumen')
        num_pivot = pd.pivot_table(dfevo, index='Cierre definitivo', values='CENTRAL', fill_value=0,
                                    aggfunc=sum)
        expander.table(num_pivot)
        expander.download_button('Descargar tabla en csv', data=convert_df(num_pivot),
                                 file_name='res_' + word + '.csv',
                                 mime='text/csv')

        fig = px.bar(dfcum, x='Cierre definitivo', y="CENTRAL", color="CENTRAL",
                     title='Cierre de centrales por año en ' + word+ ' (acumulado)')
        fig.update_xaxes(categoryorder='total descending')
        fig.update_layout(height=700)
        st.plotly_chart(fig, use_container_width=True)

        expander = st.expander('Ver y descargar tabla resumen')
        expander.table(dfcum.set_index('Cierre definitivo'))
        expander.download_button('Descargar tabla en csv', data=convert_df(dfcum.set_index('Cierre definitivo')),
                                 file_name='num_' + word + '_acum.csv',
                                 mime='text/csv')

def listado(df_fix,word):
        df_copy=df_fix.copy()
        st.subheader('Listado de centrales')
        st.write('En este apartado encontraráse la lista correspondiente a la selección elegida en el menú principal.\
        A continuación podrás filtrar entre los diferentes estado actual de las centrales: Con fecha programada,\
        en período de fin de garantía o cerradas definitivamente y podrás descargar clicando el botón correspondiente.')
        selest=st.multiselect('Elige el estado de las centrales',['CERRADA', 'FIN GARANTÍA', 'FECHA PROGRAMADA'],['CERRADA', 'FIN GARANTÍA', 'FECHA PROGRAMADA'])
        df_copy['Fin garantía'] = df_copy['Fin garantía'].dt.strftime('%d/%m/%Y')
        df_copy['Cierre definitivo']=df_copy['Cierre definitivo'].dt.strftime('%d/%m/%Y')
        df_copy = df_copy[df_copy['ESTADO'].isin(selest)]
        df_copy=df_copy[['CENTRAL','MUNICIPIO','PROVINCIA','Código MIGA','Fin garantía','Cierre definitivo']]
        st.dataframe(df_copy)
        st.download_button('Descargar listado en csv', data=convert_df(df_copy.set_index('CENTRAL')),
                        file_name='listado_centrales_' + word +'.csv',
                        mime='text/csv')

if menu=='Datos Nacionales':
        st.header('Datos Nacionales')
        recuento = dfcierre[['ESTADO', 'CENTRAL']].groupby('ESTADO').count().fillna(0).reset_index()
        indicadores_generales(dfcierre,recuento)
        grafica(dfcierre,"CAUTONOMA")
        grafica(dfcierre, "PROVINCIA")
        evotemp = dfcierre[['ESTADO','CENTRAL']].groupby([dfcierre['Cierre definitivo'].dt.year,'ESTADO']).count().reset_index()
        evoacum = dfcierre['CENTRAL'].groupby(dfcierre['Cierre definitivo'].dt.year).count().cumsum().reset_index()
        cierretemporal(evotemp,evoacum,'territorio nacional')
        listado(dfcierre,'territorio nacional')
elif menu=='Datos por Comunidad Autónoma':
        caut=st.sidebar.selectbox('Selecciona la Comunidad Autónoma',sorted(pd.unique(dfcierre['CAUTONOMA'])))
        st.header('Datos de la Comunidad Autónoma de '+caut)
        dfcierre = dfcierre[dfcierre['CAUTONOMA'] == caut]
        recuento = dfcierre[['ESTADO', 'CENTRAL']].groupby('ESTADO').count().fillna(0).reset_index()
        indicadores_generales(dfcierre, recuento)
        grafica(dfcierre, "PROVINCIA")
        evotemp = dfcierre[['ESTADO', 'CENTRAL']].groupby(
                [dfcierre['Cierre definitivo'].dt.year, 'ESTADO']).count().reset_index()
        evoacum = dfcierre['CENTRAL'].groupby(dfcierre['Cierre definitivo'].dt.year).count().cumsum().reset_index()
        cierretemporal(evotemp, evoacum, caut)
        listado(dfcierre, caut)
elif menu == 'Datos por Provincia':
        prov = st.sidebar.selectbox('Selecciona la Provincia', sorted(pd.unique(dfcierre['PROVINCIA'])))
        st.header('Datos de la Comunidad Autónoma de ' + prov)
        dfcierre = dfcierre[dfcierre['PROVINCIA'] == prov]
        #st.write(dfcierre)
        recuento = dfcierre[['ESTADO', 'CENTRAL']].groupby('ESTADO').count().fillna(0).reset_index()
        #st.write(recuento)
        indicadores_generales(dfcierre, recuento)
        evotemp = dfcierre[['ESTADO', 'CENTRAL']].groupby(
                [dfcierre['Cierre definitivo'].dt.year, 'ESTADO']).count().reset_index()
        evoacum = dfcierre['CENTRAL'].groupby(dfcierre['Cierre definitivo'].dt.year).count().cumsum().reset_index()
        cierretemporal(evotemp, evoacum, prov)
        listado(dfcierre, prov)
elif menu == 'Buscador de Central':
        st.write('En este apartado puedes introducir el código MIGA de la central para saber si aparece en el listado de \
        cierre de centrales de cobre')
        codf=st.text_input('Introduce el código MIGA y presiona el botón Enter para cargar el resultado:')
        if codf:
                try:
                        codprov= math.floor(int(codf)/100000)
                        if codprov < 1 or codprov > 53:
                                st.error('El código MIGA introduce no es válido.')
                        else:
                                res = dfcierre[dfcierre['Código MIGA']==int(codf)].copy()
                                if len(res['CENTRAL'])==0:
                                        st.write('No se ha encontrado el código MIGA en el listado, por lo cual no hay\
                                        prevista una fecha programada para esta central.')
                                        st.warning('Por si acaso, revisa el código introducido. Que no se encuentre en el\
                                                   listado no implica que el código introducido sea válido.')
                                else:
                                        st.markdown('**CÓDIGO MIGA**: {cen}'.format(cen=res['Código MIGA'].values[0]))
                                        st.markdown('**ESTADO ACTUAL**: {cen}'.format(cen=res['ESTADO'].values[0]))
                                        st.markdown('**NOMBRE DE LA CENTRAL**: {cen}'.format(cen=res['CENTRAL'].values[0]))
                                        st.markdown('**MUNICIPIO**: {mun}'.format(mun=res['MUNICIPIO'].values[0]))
                                        st.markdown('**PROVINCIA**: {mun}'.format(mun=res['PROVINCIA'].values[0]))
                                        st.markdown('**FECHA FIN DE GARANTÍA**: {mun}'.format(mun=res['Fin garantía'].dt.strftime('%d/%m/%Y').values[0]))
                                        st.markdown('**FECHA DE CIERRE**: {mun}'.format(mun=res['Cierre definitivo'].dt.strftime('%d/%m/%Y').values[0]))
                except:
                        st.error('El formato introducido no es válido.')

elif menu == 'Acerca de':
        st.header('Finalidad')
        st.write('La red de accesos de cobre de Telefónica está dividida en centrales, identificadas por un código (llamado código MIGA).\
          El progresivo despliegue de la nueva red de acceso de fibra óptica puede llevar al cierre de las antiguas\
           centrales de cobre.')
        st.write('Se entiende por cierre de una central el cese del uso de los accesos de cobre de dicha central. El cierre\
          de una central conlleva el fin de la obligación de acceso en dicha central a la red de pares de cobre de Telefónica.\
           Tras el cierre de una central, ni Telefónica ni otros operadores pueden hacer uso de los pares de cobre de esa central.')
        st.write('La Comisión Nacional de los Mercados y la Competencia (CNMC) dentro de sus concreciones y obligaciones en el\
                 ámbito de las Telecomunicaciones publica periódicamente el listado de cierre de centrales de cobre en su web de\
                  manera pública.')
        st.write('El objetivo de este proyecto es tener infomación actualizada automáticamete acerca del cierre de centrales.\
        El programa, programado en Python y desplegado gracias a la librería Streamlit y su plataforma Streamlit Sharing,\
         permite cargar automáticamente la última versión del listado de centrales de webscraping, y determina el número de\
        centrales cerradas definitivamente, en período de fin de garantía y con fecha programada comparándolas con la\
        fecha de hoy. Los datos se clasifican a nivel nacional, por comunidad autónoma y provincial. También\
        se ha habilitado un buscador de centrales por código MIGA, para poder verificar el estado actual de la central de cobre.')
        st.header('Sobre mí')
        st.write('Me llamo Álvaro Amasuno y me considero un aficionado a la analítica de datos, la programación y la IT en\
        general. Soy Ingeniero Aeronáutico por la Universidad Politécnica de Catalunya y durante el período de noviembre de 2020\
        a octubre de 2021 he sido beneficiario de una beca en la Subdirección Técnica de las Comunicaciones Electrónicas en la CNMC.')
        st.subheader('Contacto')
        st.markdown('[Perfil de LinkedIn](https://www.linkedin.com/in/%C3%A1lvaro-amasuno-arrebola-711050215/)', unsafe_allow_html=True)
        st.markdown('[@aamasuno en GitHub](https://github.com/aamasuno)', unsafe_allow_html=True)
