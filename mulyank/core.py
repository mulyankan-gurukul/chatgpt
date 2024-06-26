from langchain_openai import ChatOpenAI
from langchain.chains.router.llm_router import LLMRouterChain
from langchain.chains import create_sql_query_chain
from langchain.chains.llm import LLMChain
from langchain_community.utilities import SQLDatabase
import sqlite3
import time
from .response import OUTPUT_TEMPLATES
from mulyank.prompt_builder import QueryBuilder, RouterBuilder, OUTPUT_PROMPT, IN_PROMPT
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import text

class OutputFormatter:

    def __init__(self, destination_key):
        self.template = OUTPUT_TEMPLATES[destination_key][0]
        self.aggregation = OUTPUT_TEMPLATES[destination_key][1]

    def apply(self, agg, res):
        print(res)
        if agg == "add":
            return sum(res)
        elif agg == "concat":
            return " ".join(res)
    
    def format(self, response):
        print(response)
        if self.aggregation != None:
            response = [[self.apply(self.aggregation, response[0])]]
        inputs = {key:val for key, val in zip(self.template.input_variables, response[0])}
        print(inputs)
        return self.template.format(**inputs)

class QueryHandler:

    def __init__(self, api_key, db_loc = "sqlite:///db/mulyank.db"):
        llm = ChatOpenAI(api_key=api_key, temperature=0, seed = 0)
        self.llm = ChatOpenAI(api_key=api_key, temperature=0, seed = 0)
        self.translate_chain = LLMChain(llm = llm, prompt=IN_PROMPT)
        query_bldr = QueryBuilder()
        self.db_connection_str = db_loc
        router_bldr = RouterBuilder()
        self.router_chain = LLMRouterChain.from_llm(llm, router_bldr.get_router_prompt())
        self.query_mapping = query_bldr.get_query_mapping()
        llm1 = ChatOpenAI(api_key=api_key, temperature=0.7, seed = 0)
        self.output_chain = LLMChain(llm = llm1, prompt=OUTPUT_PROMPT)

    def run_query(self, sql_query):
        response = "Not able to connect to mulyankan database at this moment"
        engine = create_engine(self.db_connection_str)
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            response = result.fetchall()
        return response
        
    def handle_questions(self, state):
        #try:
            user_message = state.messages[-1]["content"].lower()
            print(user_message)
            user_message = self.translate_chain.invoke(input = {"message": user_message})["text"]
            print(user_message)
            destination_key = self.router_chain.invoke({"input": user_message})["destination"]
            print(destination_key)
            query = self.query_mapping[destination_key]
            print(query)
            if type(query) != str:
                query = query.format(question = user_message)
                db = SQLDatabase.from_uri(self.db_connection_str)
                write_query = create_sql_query_chain(self.llm, db)
                sql_query = write_query.invoke({"question": query})
                sql_query = sql_query.replace("```","")
                sql_query = sql_query.replace("sql\n","")
                sql_query = sql_query.strip()
                sql_query = sql_query[sql_query.find("SELECT"):]
                print("*******")
                print(sql_query)
                print("*******")
                
                response = self.run_query(sql_query)
                print(destination_key)
                response = OutputFormatter(destination_key).format(response)
                response = self.output_chain.invoke(input = {"query" : user_message, "response" : response})["text"]
            else:
                response = self.query_mapping[destination_key]
            
        #except:
        #    response = "I am sorry, I couldn't respond to this question at this time. Stay Tuned for MULYANKAN GPT updates."

            for sentence in response.split("\n"):
                for word in sentence.split(" "):
                    time.sleep(0.05)
                    yield word + " "
                yield "\n"
