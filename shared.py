# Initialize values
distance = 1.3
threshold = 17
count = 20
c_time = 10
usercode =''
operatorId=''
bedId= ''
hospitalId = 2;
wardId =0;
admin_usercode =''

#distance = 2
#threshold = 17.5
#count = 60
#time = 10

def set_values(v1, v2,v3 ,v4):
    global distance, threshold,count,c_time
    distance = v1
    threshold = v2
    count = v3
    c_time = v4

def set_distance(v1):
    global distance
    distance = v1

def set_hospitalId(v1):
    global hospitalId
    hospitalId = v1

def set_wardId(v1):
    global wardId
    wardId = v1
    
def set_threshold(v1):
    global threshold
    threshold = v1

def set_count(v1):
    global count
    count = v1

def set_time(v1):
    global c_time
    c_time = v1

def set_usercode(v1):
    global usercode
    usercode = v1
    
def set_admin_usercode(v1):
    global admin_usercode
    admin_usercode = v1
    
def set_operatorId(v1):
    global operatorId
    operatorId = v1

def set_bedId(v1):
    global bedId
    bedId = v1



def get_values():
    global distance, threshold, count, c_time
    return distance,threshold,count,c_time

def get_hospitalId():
    global hospitalId
    return hospitalId


def get_operatorId():
    global operatorId
    return operatorId
    
def get_bedId():
    global bedId
    return bedId
    
def get_distance():
    global distance
    return distance
    
def get_threshold():
    global threshold
    return threshold

def get_count():
    global count
    return count
    
def get_usercode():
    global usercode
    return usercode
    
def get_admin_usercode():
    global admin_usercode
    return admin_usercode
    
def get_time():
    global c_time
    return c_time
    
        
def get_wardId():
    global wardId
    return wardId