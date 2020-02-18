#import libraries
from flask import Flask, request
import json
import os
import glob
import yaml
import asyncio
from rasa.core.agent import Agent
from rasa import train
import nest_asyncio
import sys
sys.path.append(os.getcwd())
import aqgFunction
aqg = aqgFunction.AutomaticQuestionGenerator()
nest_asyncio.apply()

app = Flask(__name__)


#establishing  paths of the rasa bot files
global nlu_path, stories_path, models_path, domain_path, config_path, term, newdict, dictrand, train_path, agent
original_path = '.'
nlu_path = original_path + "/data/nlu.md"
stories_path = original_path + "/data/stories.md"
models_path = original_path  + "/models"
domain_path = original_path +  "/domain.yml"
config_path = original_path +  "/config.yml"
train_path =  original_path + "/data/"

list_of_files1 = glob.glob(models_path+ "/*") # * means all if need specific format then *.csv
latest_file1 = max(list_of_files1, key=os.path.getctime)
modelpath = os.path.abspath(latest_file1)

agent = Agent.load(modelpath)


# reading and creating dictionary from nlu.md file
with open(nlu_path, 'r') as f:
    text = f.readlines()
intent = None
sentences= []
term = dict()
for line in text:
    if "##" and ":" and "intent" in line:
        
        term[intent] = sentences
        sentences=[]
        intent = line.replace("##",'')
        intent = intent.replace("intent",'')
        intent = intent.replace(":",'')
        intent = intent.replace("\n",'')
        intent = intent.strip()


    else:
        line = line.replace("-",'')
        line = line.replace("\n",'')
        line = line.strip()
        sentences.append(line)
        if '' in sentences:
            sentences.remove('')
term[intent] = sentences
filtered = {k: v for k, v in term.items() if k is not None}
term.clear()
term.update(filtered)


#reading and creating dictionary from domain.yml file
with open(domain_path) as g:
    data1 = yaml.load(g, Loader=yaml.FullLoader)
data2 = data1["templates"]
newdict=dict()
for keys in data2:

    data3 = data2[keys]
    data4=data3[0]
    data5 = data4["text"]
    newdict[keys]= data5
    
dictrand={}
with open(stories_path, 'r') as h:
    text2 = h.readlines()
for line8 in text2:

    if "*" in line8:
        line9 = line8.replace("*","")
        line9= line9.strip()
        if line9 in list(term.keys()):
            first = line9
            
    if "##" not in line8 and "*" not in line8 and "-" in line8:
        line6 = line8.replace("-","")
        line6 = line6.strip()
        if line6 in list(newdict.keys()):
            second = line6
            dictrand[first]= second
            



#predict intent service
@app.route("/predict", methods=['POST'])
def predict():
    jsonObject = json.loads(request.data)
    query = jsonObject['question']
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    Prediction = asyncio.run(agent.parse_message_using_nlu_interpreter(message_data=query, tracker=None))
    Prediction = Prediction["intent"]['name']
    
    return Prediction


#add intent service
@app.route("/newintent", methods=['POST'])
def newintent():
    global term, newdict, dictrand
    jsonObject = json.loads(request.data)
    intent_name = jsonObject['name_intent']
    questions = jsonObject['ques']
    response = jsonObject['respond']
    
    if len(intent_name) == 0 or len(response) == 0:
        
        return {"message": "enter required fields"}
        
    elif len(questions)<5 :
        
        return {"message": "Number of Questions not sufficient"}
    
    else:
        
        if intent_name == 'default' or intent_name in list(term.keys()) or "intent" in intent_name:
            
            return {"message": "Intent Name Not Accepted"}
        else:
            
            intent = intent_name
            response = response
            action = "utter_"+intent
            Questions = questions
            
            term[intent] = Questions
            newdict[action] = response
            dictrand[intent] = action
            
            file_handler = open(nlu_path,'w')
            for finalkeys in list(term.keys()):

                file_handler.write('\n'+ "## intent:")
                file_handler.write(finalkeys)

                for value in term[finalkeys]:

                    file_handler.write('\n'+ "- " + value)

                file_handler.write('\n')
            file_handler.close()
            
            dictaction= dict()
            for k,v in newdict.items():
                dictaction[k] = [{"text" : v}]
            
            finaldict = {'actions': list(newdict.keys()), "intents" : list(term.keys()), "templates": dictaction}
            
            with open(domain_path, 'w') as file:
                yaml.dump(finaldict, file)
            
            file_handler = open(stories_path,'w')
            for key2 in dictrand:
                file_handler.write('\n'+ "## " + "path_" + key2 )
                file_handler.write('\n'+ "* " + key2)
                file_handler.write('\n'+ "  - " + dictrand[key2])

                file_handler.write('\n')
            file_handler.close()
            
            return {"message": "Intent Added"}

        
#remove intent service        
@app.route("/removeintent" , methods=['POST'])
def Rem1():
    global term, newdict, dictrand
    jsonObject = json.loads(request.data)
    intent_name = jsonObject['name_intent']
    
    
    if intent_name=='':
        return {'message': 'Please Enter Intent.'}
    else:
        req1 = intent_name
        req2 = "utter_" + req1
        del term[req1]
        del newdict[req2]
        del dictrand[req1]
        
        file_handler = open(nlu_path,'w')
        for finalkeys in list(term.keys()):

            file_handler.write('\n'+ "## intent:")
            file_handler.write(finalkeys)

            for value in term[finalkeys]:

                file_handler.write('\n'+ "- " + value)

            file_handler.write('\n')
        file_handler.close()

        dictaction= dict()
        for k,v in newdict.items():
            dictaction[k] = [{"text" : v}]

        finaldict = {'actions': list(newdict.keys()), "intents" : list(term.keys()), "templates": dictaction}

        with open(domain_path, 'w') as file:
            yaml.dump(finaldict, file)

        file_handler = open(stories_path,'w')
        for key2 in dictrand:
            file_handler.write('\n'+ "## " + "path_" + key2 )
            file_handler.write('\n'+ "* " + key2)
            file_handler.write('\n'+ "  - " + dictrand[key2])

            file_handler.write('\n')
        file_handler.close()
        
        return {"message": "intent removed"}             

        
#model training service        
@app.route("/train" , methods=['POST'])
def train_model():
    global agent
    #os.chdir(original_path)
    asyncio.set_event_loop(asyncio.new_event_loop())
    train(domain= domain_path, config= config_path, training_files= train_path, force_training=False)
    
    list_of_files = glob.glob(models_path + '/*') 
    latest_file = max(list_of_files, key=os.path.getctime)
    modelpath1 = os.path.abspath(latest_file)
    
    agent = Agent.load(modelpath1)
    
    return {"message": "training done"}



#adding sentence to intent service
@app.route("/AddComponent" , methods=['POST'])
def Add():
    global term
    jsonObject = json.loads(request.data)
    intent_name = jsonObject['name_intent']
    component = jsonObject['comp']
    list3 = term[intent_name]
    
    if len(component) == 0 :
        
        return {"message": "select required fields"}
    
    list3.append(component)
    
    tup = list3
    term[intent_name] = tup
    file_handler = open(nlu_path,'w')
    for finalkeys in list(term.keys()):

        file_handler.write('\n'+ "## intent:")
        file_handler.write(finalkeys)

        for value in term[finalkeys]:

            file_handler.write('\n'+ "- " + value)

        file_handler.write('\n')
    file_handler.close()
    
    current = list()
    current.append(component)
    return {'message' : 'Component added'}
    
    

#removing sentence from intent service
@app.route("/RemoveComponent" , methods=['POST'])
def Rem():
    global term
    jsonObject = json.loads(request.data)
    component1 = jsonObject['comp1']
    intent_name = jsonObject['name_intent']
    
    
    if len(component1) == 0 :
        
        return {"message":"please enter required fields"}
    else:
        
        pick8 = term[intent_name]
        if component1 in pick8:
            pick8.remove(component1)
            term[intent_name] = pick8
            
            file_handler = open(nlu_path,'w')
            for finalkeys in list(term.keys()):

                file_handler.write('\n'+ "## intent:")
                file_handler.write(finalkeys)

                for value in term[finalkeys]:

                    file_handler.write('\n'+ "- " + value)

                file_handler.write('\n')
            file_handler.close()
            return {"message":"Component removed"}
        
        else:
            return {'message':'Sentence not present'}
            
    

#generate questions from corpus service
@app.route("/corpusQuestions" , methods=['POST'])
def corpus():
    jsonObject = json.loads(request.data)
    inputText = jsonObject['Corpus']
    questionList = aqg.aqgParse(inputText)
    for x in range(questionList.count('\n')):
        questionList.remove('\n')
    
    return {"questions": questionList}




#get intent list
@app.route("/intentlist", methods=['POST'])
def intentlist():
    list1= list(term.keys())   
    return {"intents": list1}



#getQuestions and Response for an intent
@app.route("/QandR", methods=['POST'])
def QandR():
    jsonObject = json.loads(request.data)
    intentname = jsonObject['iname']
    qlist = term[intentname]
    interm = "utter_"+intentname
    res = newdict[interm]    
    return {"Qlist": qlist,"Response":res}

    
    
    




    
    
    
    
    