def tweet_factory(cursor, row):
    ret = {}
    for index, key in enumerate(cursor.description):
        ret[key[0]] = row[index]
    
    return ret
