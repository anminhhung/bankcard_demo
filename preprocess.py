LIST_FIRSTNAME_PREPROCESS = ["NGUYEN", "AN", "PHAM", "DANG", "PHAN", "TRAN", "HUYNH"]
LIST_MIDNAME_PREPROCESS = ["VAN", "THI"]

def checkmonth(month):
    if month > 12:
        return True
    
    return False

def replace_char_to_number(number):
    number = number.replace('b', '6')

    return number