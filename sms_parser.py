#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 14:00:21 2020

@author: aviallon
"""

from lxml.etree import XMLParser, parse
from io import BytesIO
import datetime
import argparse
 
    
def get_date(timestamp):
    timestamp = int(timestamp)
    from datetime import datetime
    # Timestamps are in milliseconds since epoch
    dt = datetime.fromtimestamp(timestamp//1000)
    return dt
    
def get_date_str(timestamp):
    dt = get_date(timestamp)
    return f"{dt.year}-{dt.month}-{dt.day} {dt.hour}:{dt.minute}:{dt.second}.{timestamp % 1000}"

def get_discussion(messages, correspondant, threshold=60, merge_threshold=30):
    msgs = messages[correspondant]
    discussions = []
    current_discussion = []
    for i,msg in enumerate(msgs):
        date = get_date(msg["timestamp"])
        msg["body"] = msg["body"].strip()
        if not(len(msg["body"])):
            continue
        if "ce correspondant a cherché à vous joindre" in msg["body"]:
            continue
        # if msg["body"][-1] not in ".?!":
        #     msg["body"] += "."
        if not(len(current_discussion)):
            current_discussion.append(msg)
        else:
            last_date = get_date(current_discussion[-1]["timestamp"])
            if (date - last_date) < datetime.timedelta(minutes=threshold):
                if (date - last_date) < datetime.timedelta(seconds=merge_threshold) and current_discussion[-1]["me"] == msg["me"]:
                    current_discussion[-1]["body"] = current_discussion[-1]["body"].strip() + "\n" + msg["body"]
                    current_discussion[-1]["timestamp"] = msg["timestamp"]
                else:
                    current_discussion.append(msg)
            else:
                discussions.append(current_discussion[:])
                current_discussion.clear()
                
    if len(current_discussion):
        discussions.append(current_discussion[:])
    
    print(f"Il y a {len(discussions)} disscussions au total")
    return discussions


def get_msg_pairs(discussions):
    paires = []
    for discussion in discussions:
        i = 0
        while i < len(discussion)-1:
            msg = discussion[i]
            next_msg = discussion[i+1]
            #print(msg)
            if msg["timestamp"] > next_msg["timestamp"]:
                msg, next_msg = next_msg, msg
            if msg["me"] or (not(msg["me"]) and not(next_msg["me"])):
                i += 1
                continue
            paires.append((msg["body"], next_msg["body"]))
            i += 2
        return paires
    
def remove_accents(input_str):
    import unicodedata
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii
    
def tokenize_msg(msg):
    msg = remove_accents(msg).decode("ascii")
    msg = msg.replace("\n", " ")
    return msg
    
def msg_pairs_to_simple(paires):
    simple = ""
    if not(paires):
        return ""
    for paire in paires:
        question, answer = tokenize_msg(paire[0]), tokenize_msg(paire[1])
        simple += f"Question : {question}\nAnswer : {answer}\n"
    return simple




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parses XML files outputed by Super Backup or Silence into something LARA can understand")
    parser.add_argument("input_file", help="XML file to read from")
    parser.add_argument("-o", dest="output_file", default="data_sms.txt", help="Specify the output file")
    
    args = parser.parse_args()
    
    
    lxml_parser = XMLParser(huge_tree = True, recover = True)

    payload = open(args.input_file, "rb").read().decode("utf-8")
    
    payload = payload.encode ('utf-16', 'surrogatepass').decode ('utf-16')
    payload = payload.encode ('utf-8')
    
    tree = parse (BytesIO (payload), parser = lxml_parser)
    root = tree.getroot()
    
    messages = {}
    
    for msg in root.getchildren():
        msgdata = dict(zip(msg.keys(), msg.values()))
        num = msgdata['address']
        msgdata = {"timestamp":int(msgdata["date"]), "body":msgdata["body"], "me":msgdata["type"] == '2'}
        num = num.replace(' ', '')
        if messages.get(num) is None:
            messages[num] = []
        messages[num].append(msgdata)
    
    discussions = {}
    pairs = {}
    simple = ""
    print("Correspondants:")
    for correspondant in messages.keys():
        print(correspondant)
        discussions[correspondant] = get_discussion(messages, correspondant, threshold=60, merge_threshold=30)
        pairs[correspondant] = get_msg_pairs(discussions[correspondant])
        simple += msg_pairs_to_simple(pairs[correspondant])
        
    with open(args.output_file, "w") as f:
        f.write(simple)