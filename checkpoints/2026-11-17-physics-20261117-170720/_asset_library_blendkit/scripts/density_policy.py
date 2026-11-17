RANGES={'low':(10,20),'medium':(30,50),'high':(70,80)}
def count_for(seed,level):
    import random
    return random.Random(str(seed)+level).randint(*RANGES[level])
def repeat_cap(record):
    if record['category'] in ('bag','luggage','clothing','footwear','towel'):return 1
    return 3

