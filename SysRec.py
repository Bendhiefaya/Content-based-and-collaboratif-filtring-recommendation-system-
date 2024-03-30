# -*- coding: utf-8 -*-
"""


@author: bendh
"""

import nltk
import mysql.connector
import numpy

from nltk.stem.snowball import EnglishStemmer

from nltk.corpus import stopwords

from scipy import spatial


#--connexion a la base de donnnee
conn = mysql.connector.connect(host="localhost",user="root",password="",database="sys_rec_test")
print(" ---------------------------------------------------- ")
print("|Welcome to BIBTECH Library : An Elite Online Library|")
print(" ---------------------------------------------------- ")
print("|                                                    |")
print(" ---------------------------------------------------- ")
print("|                                                    |")
print("|  To get the best reccomandation enter book name    |")
print("|                                                    |")
bookName=str(input("|     Book Name:  "))
print("|                                                    |")

#////////////////////////////////////////////////////////////////  
#////////////////////////////////////////////////////////////////        
# SYS rec base sur le contenu 
#////////////////////////////////////////////////////////////////
#//////////////////////////////////////////////////////////////// 

#--declaration du curseur
cursor = conn.cursor()
print(" --------------------------------------------------- ")
print("|      connexion etablie                            |")
print(" --------------------------------------------------- ")

#--recuperation des donnees de la base
cursor.execute("select * from product")
rows = cursor.fetchall()


# liste des stops words dans la langue "english"
stop=list(stopwords.words('english'))
stop.extend([".",",",":",";","'","!",")","(","+","''","-"])

#Dectionnaire pour les description
dictDescription={}
#liste des mots en totalite
listTotaliteMots=set()

for row in rows :
    idpdt = row[0]
    description = row[3]
    
    #-- 1ere phase Tokenisation :
    mots = nltk.word_tokenize(description)
   
    #-- 2eme phase Steming :
    stemmer=EnglishStemmer()
    motsStems=[]
    for m in mots:
        motsStems.append(stemmer.stem(m))
    
    #-- 3eme phase  :
    motsFinal=[];
    for m in motsStems:
        if m not in stop :
            motsFinal.append(m)
            
    listUniqueMots=set(motsFinal) 
    for m in listUniqueMots:
        listTotaliteMots.add(m)
        
    dictDescription[idpdt]=listUniqueMots
    
############# ##########################################    
# RESULTAT 1 dictDescription={ IDBook:{list of unique stems} }
#######################################################


# df un dictionnaire qui donne le nombre de livre qui contiennet le mot
df={}
for m in listTotaliteMots:
    nbr=0
    for i in range(len(dictDescription)):
        if m in dictDescription[i+1]:
            nbr+=1
    df[m]=nbr

# calculer TF et IDF
# Creation de la matrice de frequence:
# declaration et initialisation de la matrice a zeros
matriceBinaire=numpy.zeros((len(dictDescription),len(listTotaliteMots)))

TF=0;
IDF=0; 
for i in range(len(dictDescription)):
    j=0
    for m in listTotaliteMots:
        if m in dictDescription[i+1]:
            TF=df[m]/len(listTotaliteMots)
            IDF=numpy.log(len(dictDescription)/df[m])
            matriceBinaire[i][j]=TF*IDF;
        j+=1

#######################################################
#fermer le cursor :
cursor.close()
# calcul de similarite sur la base de matrice
def similariteJaccard(idpdt1,idpdt2):
    return(1-spatial.distance.jaccard(matriceBinaire[idpdt1], matriceBinaire[idpdt2]))      

# matrice de similarite : ultime objectif 
matriceSimilarite=numpy.zeros((len(dictDescription),len(dictDescription)))

for i in range(len(dictDescription)):
    for j in range(len(dictDescription)):
        matriceSimilarite[i][j]=similariteJaccard(i, j)

#  donner a chaque livre l' id des 3 livres qui lui sont similaires
cursor = conn.cursor()
cursor.execute("select IDBook from product where BookName=\""+bookName+"\"")
inputLiv=cursor.fetchone()
liv=int(inputLiv[0]/1000)

livre1=0
livre2=0
livre3=0

max1=0
i=0
for sim in matriceSimilarite[liv]:
    if( sim>max1 and sim<0.999):
        max1=sim
        livre1=i+1
    i+=1   

max2=0
j=0
for sim in matriceSimilarite[liv]:
    if (sim>max2 and sim<0.999 and sim!=max1):
        max2=sim
        livre2=j+1
    j+=1   

max3=0
k=0
for sim in matriceSimilarite[liv]:
    if (sim>max3 and sim<0.999 and sim!=max1 and sim!=max2):
        max3=sim
        livre3=k+1
    k+=1   
print(" --------------------------------------------------- ")
print("|      Voir encore :                                |")  
cursor.execute("select BookName from product where IDBook="+str(livre1))
NameLivre1=cursor.fetchone()  
print("|           1-",NameLivre1[0])
cursor.execute("select BookName from product where IDBook="+str(livre2))
NameLivre2=cursor.fetchone()  
print("|           2-",NameLivre2[0])
cursor.execute("select BookName from product where IDBook="+str(livre3))
NameLivre3=cursor.fetchone()  
print("|           3-",NameLivre3[0])
print(" --------------------------------------------------- ")
#////////////////////////////////////////////////////////////////  
#////////////////////////////////////////////////////////////////        
# FILTRAGE COLLABORATIVE 
#////////////////////////////////////////////////////////////////
#////////////////////////////////////////////////////////////////  
cursor = conn.cursor()
cursor.execute("select * from user")
rows = cursor.fetchall()

nbrUser = len(rows)
cursor.close()

nbrArticle=len(dictDescription)

# creation et initialisation a zeros de la matrice des note
matriceNotes=numpy.zeros((nbrUser,nbrArticle))
#connexion a la base de donnees pour remplir cet matrice a partir de la table rating

"""
        article
    user    0    a   b    c   d   e    .     .
     0
     1     
     2
     3
     4
     .
     .
"""
cursor = conn.cursor()
for i in range(nbrUser):
    cursor.execute("select * from rating where IDUser="+str((i+1)*1000))
    rows = cursor.fetchall()
    j=0
    for row in rows:
        note=row[3]
        matriceNotes[i][j]=note
        j+=1
cursor.close()


#construction de la matrice de similarite de USER
matriceSimilariteUser = numpy.zeros((nbrUser,nbrUser))

def similariteJaccard2(i,j):
    return(1-spatial.distance.jaccard(matriceNotes[i], matriceNotes[j]))     

for u1 in range(nbrUser):
    for u2 in range(nbrUser):
        matriceSimilariteUser[u1,u2]= similariteJaccard2(u1,u2)
print(" --------------------------------------------------- ")
print("|   in our DataBase we have 6 Users and 10 Books:   |")
print("|   to predict any rating please enter :            |")
inputUserId=int(input("|        the user id:"))
inputBookName=str(input("|        enter the book name:"))
userRecherche=int(inputUserId/1000)

cursor = conn.cursor()
cursor.execute("select IDBook from product where BookName=\""+inputBookName+"\"")
inputLivName=cursor.fetchone()
inputBookId=int(inputLivName[0]/1000)

articleRecherche=inputBookId
#print("la ligne des similarites considerees est :",matriceSimilariteUser[userRecherche-1])

voisin1=-1
voisin2=-1
voisin3=-1

max1=0
i=0
for sim in matriceSimilariteUser[userRecherche-1]:
    if sim>max1 and sim<0.99:
        max1=sim
        voisin1=i
    i+=1     

max2=0
i=0
for sim in matriceSimilariteUser[userRecherche-1]:
    if sim>max2 and sim<0.99 and sim!=max1:
        max2=sim
        voisin2=i
    i+=1   

max3=0
i=0
for sim in matriceSimilariteUser[userRecherche-1]:
    if sim>max3 and sim<0.99 and sim!=max1 and sim!=max2:
        max3=sim
        voisin3=i
    i+=1   

notePredite = float((max1*matriceNotes[voisin1][articleRecherche-1]+max2*matriceNotes[voisin2][articleRecherche-1]+max3*matriceNotes[voisin3][articleRecherche-1])/(max1+max2+max3))

matriceNotes[userRecherche-1][articleRecherche-1]= notePredite

print(" --------------------------------------------------- ")
if(notePredite == 0.0):
    print("|    prediction : user already rated this book")
else:
    print("|    prediction ",str(inputUserId),"-",inputBookName,":",notePredite)
print(" --------------------------------------------------- ")

cursor.close()


































