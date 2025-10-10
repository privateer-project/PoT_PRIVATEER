import sympy
from ctypes import *
import os
import numpy as np
import sys
import json
import os
import ctypes

# Struct `mu` definition in Python
class Mu(ctypes.Structure):
    _fields_ = [
        ('M', ctypes.c_uint),
        ('a', ctypes.c_int),
        ('s', ctypes.c_int)
    ]

# Load shared library (.so) which contains C functions
magic_lib = ctypes.CDLL('parameters_generation/magic_numbers/magic_num.so')

magicu = magic_lib.magicu
magicu.argtypes = [ctypes.c_uint]
magicu.restype = Mu

# Size of the scenario in number of nodes
SIZE = int(sys.argv[1])

NOPOT = int(sys.argv[2])
# Prime number to perform operations, will be set as a parameter in the future
p = 67 #67

# Polynomial definitions
def pol_1(size, p):
    coeff = [np.random.randint(-50, 50) for i in range(size)]
    poly = lambda x: sum([np.int64(c) * np.int64(x)**np.int64(i) for i, c in enumerate(coeff)]) % np.int64(p)
    return poly, coeff

def pol_2(size, p):
    coeff = [0] + [np.random.randint(-50, 50) for i in range(1, size)]
    poly = lambda x: sum([np.int64(c) * np.int64(x)**np.int64(i) for i, c in enumerate(coeff)]) % np.int64(p)
    return poly, coeff

# Function to calculate lpcs
def handle_calculate_lpcs(x_points, prime):
    lpcs = []

    for i in range(0, len(x_points)):
        x_points = np.array(x_points, dtype=np.int64)
        top = np.int64(1)
        bot = np.int64(1)
        for j in range(len(x_points)):
            if i != j:
                top = top * np.int64(-x_points[j])
                bot = bot * np.int64(x_points[i] - x_points[j])
        lpc_value = (top * sympy.mod_inverse(bot, prime)) % prime
        # print("LPC" + str(i) + ": " + str((top * modinv(bot, prime)) % prime))
        lpcs.append(lpc_value)
    return lpcs

# Generate SIZE random points
x = np.random.randint(-p+1,p, size=(SIZE)) #(-p+1,p, size=(SIZE))

poly1,coeff1 = pol_1(SIZE, p)

# Buid secret polynomial
poly_str = "Secret Polynomial: "
for i, c in enumerate(coeff1):
    if i == 0:
        poly_str += f"{c}"
    else:
        poly_str += f" + {c}x^{i}"

# Print secret polynomial
print(poly_str)

poly2,coeff2 = pol_2(SIZE, p)

# Build public polynomial
poly_str = "Public Polynomial: "
for i, c in enumerate(coeff2):
    if i == 0:
        poly_str += f"{c}"
    else:
        poly_str += f" + {c}x^{i}"

# Print public polynomial
print(poly_str)

# Calculate polynomial points and lpcs
y1 = [poly1(i) for i in x]
y2 = [poly2(i) for i in x]
y1_noTTL = y1
lpc = handle_calculate_lpcs(x,p)

ttl_list = np.arange(64, 64 - SIZE, -1) #64 - numero de nodos
#Substract the ttl value of each jump
y1 = (y1 - ttl_list) % np.int64(p)

opot_masks = []
size = 16 

# Generate OPoT masks
for i in range(2*(SIZE-1)):
    opot_masks.append(os.urandom(size).hex())
      
# Generate magic numbers for given prime number
magic = magicu(p)

# Print info
print("p",p)
print("x",x)
print("y1",y1_noTTL)
print("y1 with TTL",y1)
print("y2",y2)
print("LPC",lpc)
print(opot_masks) 
print(f'M: {magic.M}, s: {magic.s}, a: {magic.a}')

# Build parameters json file

datos = {
    "switches" : [
      {
        "name": "ingressNode",
        "address": "10.0.0.11:9559",
        "device_id": 0,
        "proto_dump_file": "logs/ingressNode-p4runtime-requests.txt",
        "routing_rules": [
            {
                "match":
                    {
                        "dstAddr":"10.1.2.3",
                        "prefix_len": 32,
                        "ingress_port": 1
                    }
                ,
                "action_params":
                    {
                        "srcAddr":"02:42:0a:00:01:03",
                        "dstAddr":"02:42:0a:00:01:02",
                        "port": 2
                    }
                
            },
            {
                "match":
                    {
                        "dstAddr":"10.1.1.3",
                        "prefix_len": 32,
                        "ingress_port": 2
                    }
                ,
                "action_params":
                    {
                        "srcAddr":"02:42:0a:01:01:02",
                        "dstAddr":"02:42:0a:01:01:03",
                        "port": 1
                    }
                
            },
            {
                "match":
                    {
                        "dstAddr":"10.1.1.4",
                        "prefix_len": 32,
                        "ingress_port": 2
                    }
                ,
                "action_params":
                    {
                        "srcAddr":"02:42:0a:01:01:02",
                        "dstAddr":"02:42:0a:01:01:04",
                        "port": 1
                    }
                
            }
        ],
        "pot_ingress_rules": [
            {
                "match":
                    {
                        "servicePathIdentifier": 0,
                        "serviceIndex": 0,
                        "dstAddr":"10.1.2.3"
                    }
                ,
                "action_params":
                    {
                        "prime": p,
                        "identifier": 55,
                        "serviceIndex": SIZE,
                        "secretShare": int(y1[0]),
                        "publicPol": int(y2[0]),
                        "lpc": int(lpc[0]),
                        "upstreamMask": int(opot_masks[0],16),
                        "magic_M": magic.M,
                        "magic_a": magic.a,
                        "magic_s": magic.s
                    }
                
            }
        ],
        "pot_forward_rules":[],
        "pot_egress_rules": [
            {
                "match":
                    {
                        "servicePathIdentifier": 23,
                        "serviceIndex": 1,
                        "dstAddr":"10.1.1.3"
                    },
                "action_params":
                    {
                        "prime": p,
                        "secretShare": int(y1[SIZE-1]),
                        "publicPol": int(y2[SIZE-1]),
                        "lpc": int(lpc[SIZE-1]),
                        "downstreamMask": int((opot_masks[len(opot_masks)-1]),16),
                        "validator_key": int(poly1(0)),
                        "magic_M": magic.M,
                        "magic_a": magic.a,
                        "magic_s": magic.s
                    }
                
            },
            {
                "match":
                    {
                        "servicePathIdentifier": 66,
                        "serviceIndex": 1,
                        "dstAddr":"10.1.1.4"
                    },
                "action_params":
                    {
                        "prime": p,
                        "secretShare": int(y1[SIZE-1]),
                        "publicPol": int(y2[SIZE-1]),
                        "lpc": int(lpc[SIZE-1]),
                        "downstreamMask": int((opot_masks[len(opot_masks)-1]),16),
                        "validator_key": int(poly1(0)),
                        "magic_M": magic.M,
                        "magic_a": magic.a,
                        "magic_s": magic.s
                    }
                
            }
        ],
        "metrics_rules":[
            {
                "action_params":
                    {
                        "srcAddr":"02:42:0a:00:00:0b",
                        "dstAddr":"02:42:0a:00:00:0a",
                        "port": 3,
                        "ipSrcAddr":"10.0.0.11",
                        "ipDstAddr":"10.0.0.10"
                    }
                
            }
        ],
        "clone_rules":[
            {
                "match":
                {
                    "dstAddr":"10.1.1.3",
                    "prefix_len": 32,
                    "ingress_port": 2
                } ,
                  
            },
            {
                "match":
                {
                    "dstAddr":"10.1.1.4",
                    "prefix_len": 32,
                    "ingress_port": 2
                } ,
                  
            },
            {
                "match":
                {
                    "dstAddr":"10.1.2.3",
                    "prefix_len": 32,
                    "ingress_port": 1
                } 
            }
        ]
      },
      {
        "name": "egressNode",
        "address": f"10.0.0.{SIZE+10}:9559",
        "device_id": 0,
        "proto_dump_file": "logs/egressNode-p4runtime-requests.txt",
        "routing_rules": [
            {
                "match":
                    {
                        "dstAddr":"10.1.2.3",
                        "prefix_len": 32,
                        "ingress_port": 1
                    }
                ,
                "action_params":
                    {
                        "srcAddr":"02:42:0a:01:02:02",
                        "dstAddr":"02:42:0a:01:02:03",
                        "port": 2
                    },
                
            },
            {
                "match":
                    {
                        "dstAddr":"10.1.1.3",
                        "prefix_len": 32,
                        "ingress_port": 2
                    },
                     
                "action_params":
                    {
                        "srcAddr": f"02:42:0a:00:{(SIZE-1):02x}:02",
                        "dstAddr": f"02:42:0a:00:{(SIZE-1):02x}:03",
                        "port": 1
                    },
            },
            {
                "match":
                    {
                        "dstAddr":"10.1.1.4",
                        "prefix_len": 32,
                        "ingress_port": 2
                    },
                     
                "action_params":
                    {
                        "srcAddr": f"02:42:0a:00:{(SIZE-1):02x}:02",
                        "dstAddr": f"02:42:0a:00:{(SIZE-1):02x}:04",
                        "port": 1
                    },
            },

        ],
        "pot_ingress_rules": [
            {
                "match":
                    {
                        "servicePathIdentifier": 0,
                        "serviceIndex": 0,
                        "dstAddr":"10.1.1.3"
                    }
                ,
                "action_params":
                     {
                        "prime": p,
                        "identifier": 23,
                        "serviceIndex": SIZE,
                        "secretShare": int(y1[0]),
                        "publicPol": int(y2[0]),
                        "lpc": int(lpc[0]),
                        "upstreamMask": int(opot_masks[SIZE -1],16),
                        "magic_M": magic.M,
                        "magic_a": magic.a,
                        "magic_s": magic.s
                    },
            
            },
            {
                "match":
                    {
                        "servicePathIdentifier": 0,
                        "serviceIndex": 0,
                        "dstAddr":"10.1.1.4"
                    }
                ,
                "action_params":
                     {
                        "prime": p,
                        "identifier": 66,
                        "serviceIndex": SIZE,
                        "secretShare": int(y1[0]),
                        "publicPol": int(y2[0]),
                        "lpc": int(lpc[0]),
                        "upstreamMask": int(opot_masks[SIZE -1],16),
                        "magic_M": magic.M,
                        "magic_a": magic.a,
                        "magic_s": magic.s
                    },
            
            }
        ],
        "pot_forward_rules":[],
        "pot_egress_rules": [
            {
                "match":
                    {
                        "servicePathIdentifier": 55,
                        "serviceIndex": 1,
                        "dstAddr":"10.1.2.3"
                    }
                ,
                "action_params":
                    {
                        "prime": p,
                        "secretShare": int(y1[SIZE-1]),
                        "publicPol": int(y2[SIZE-1]),
                        "lpc": int(lpc[SIZE-1]),
                        "downstreamMask": int(opot_masks[SIZE-2],16),
                        "validator_key": int(poly1(0)),
                        "magic_M": magic.M,
                        "magic_a": magic.a,
                        "magic_s": magic.s
                    }
                
            }
        ],
        "metrics_rules":[
            {
                "action_params":
                    {
                        "srcAddr":f"02:42:0a:00:00:{(SIZE+10):02x}",
                        "dstAddr":"02:42:0a:00:00:0a",
                        "port": 3,
                        "ipSrcAddr":f"10.0.0.{SIZE+10}",
                        "ipDstAddr":"10.0.0.10"
                    }
                
            }
        ],
        "clone_rules":[
            {
                "match":
                {
                    "dstAddr":"10.1.1.3",
                    "prefix_len": 32,
                    "ingress_port": 2
                } 
                
            },
            {
                "match":
                {
                    "dstAddr":"10.1.1.4",
                    "prefix_len": 32,
                    "ingress_port": 2
                } 
                
            },
            {
                "match":
                {
                    "dstAddr":"10.1.2.3",
                    "prefix_len": 32,
                    "ingress_port": 1
                } 
            }
        ]
      },
      {
        "name": "middleNode2",
        "address": f"10.0.0.13:9559",
        "device_id": 0,
        "proto_dump_file": "logs/middleNode2-p4runtime-requests.txt",
        "routing_rules": [
            {
                "match":
                    {
                        "dstAddr":"10.1.2.3",
                        "prefix_len": 32,
                        "ingress_port": 1
                    }
                ,
                "action_params":
                    {
                        "srcAddr":"02:42:0a:01:03:03",
                        "dstAddr":"02:42:0a:01:03:02",
                        "port": 2
                    },
                
            },
            {
                "match":
                    {
                        "dstAddr":"10.1.1.3",
                        "prefix_len": 32,
                        "ingress_port": 2
                    },
                     
                "action_params":
                    {
                        "srcAddr": f"02:42:0a:00:{(SIZE + NOPOT - 1):02x}:02",
                        "dstAddr": f"02:42:0a:00:{(SIZE + NOPOT - 1):02x}:03",
                        "port": 1
                    },
            },
            {
                "match":
                    {
                        "dstAddr":"10.1.1.4",
                        "prefix_len": 32,
                        "ingress_port": 2
                    },
                     
                "action_params":
                    {
                        "srcAddr": f"02:42:0a:00:{(SIZE + NOPOT - 1):02x}:02",
                        "dstAddr": f"02:42:0a:00:{(SIZE + NOPOT - 1):02x}:01",
                        "port": 1
                    },
            },

        ],
        "pot_ingress_rules": [

        ],
        "pot_forward_rules":[
                {
                    "match":
                        {
                            "servicePathIdentifier": 55,
                            "serviceIndex": SIZE-2,
                            "dstAddr":"10.1.2.3"
                        }
                    ,
                    "action_params":
                        {
                            "prime": p,
                            "secretShare": int(y1[2]),
                            "publicPol": int(y2[2]),
                            "lpc": int(lpc[2]),
                            "upstreamMask": int(opot_masks[2],16),
                            "downstreamMask": int(opot_masks[2-1],16),
                            "magic_M": magic.M,
                            "magic_a": magic.a,
                            "magic_s": magic.s
                        }
                    
                },
                {
                    "match":
                        {
                            "servicePathIdentifier": 23,
                            "serviceIndex": 2+1,
                            "dstAddr":"10.1.1.3"
                        }
                    ,
                    "action_params":
                        {
                            "prime": p,
                            "secretShare": int(y1[SIZE-1-2]),
                            "publicPol": int(y2[SIZE-1-2]),
                            "lpc": int(lpc[SIZE-1-2]),
                            "upstreamMask": int(opot_masks[len(opot_masks)-2],16),
                            "downstreamMask": int(opot_masks[len(opot_masks)-2-1],16),
                            "magic_M": magic.M,
                            "magic_a": magic.a,
                            "magic_s": magic.s
                        }
                    
                }
            ],
        "pot_egress_rules": [
        ],
        "metrics_rules":[
            {
                "action_params":
                    {
                        "srcAddr":"02:42:0a:00:00:0d",
                        "dstAddr":"02:42:0a:00:00:0a",
                        "port": 3,
                        "ipSrcAddr":"10.0.0.13",
                        "ipDstAddr":"10.0.0.10"
                    }
                
            }
        ],
        "clone_rules":[
            {
                "match":
                {
                    "dstAddr":"10.1.1.3",
                    "prefix_len": 32,
                    "ingress_port": 2
                } 
                
            },
            {
                "match":
                {
                    "dstAddr":"10.1.1.4",
                    "prefix_len": 32,
                    "ingress_port": 2
                } 
                
            },
            {
                "match":
                {
                    "dstAddr":"10.1.2.3",
                    "prefix_len": 32,
                    "ingress_port": 1
                } 
            }
        ]
      }
    ]
  }

for i in range(1,SIZE -1):
    if i == 2:
        continue

    datos["switches"].append(
            {
            "name": f"middleNode{i}",
            "address": f"10.0.0.{i+11}:9559",
            "device_id": 0,
            "proto_dump_file": f"logs/middleNode{i}-p4runtime-requests.txt",
            "routing_rules": [
                {
                    "match":
                        {
                            "dstAddr":"10.1.2.3",
                            "prefix_len": 32,
                            "ingress_port": 1
                        }
                    ,
                    "action_params":
                        {
                            "srcAddr":f"02:42:0a:00:{(i+1):02x}:03",
                            "dstAddr":f"02:42:0a:00:{(i+1):02x}:04",
                            "port": 2
                        }
                    
                },
                {
                    "match":
                        {
                            "dstAddr":"10.1.1.3",
                            "prefix_len": 32,
                            "ingress_port": 2
                        }
                    ,
                    "action_params":
                        {
                            "srcAddr":f"02:42:0a:00:{(i):02x}:02",
                            "dstAddr":f"02:42:0a:00:{(i):02x}:03",
                            "port": 1
                        }
                    
                }
            ],
            "pot_ingress_rules": [

            ],
            "pot_forward_rules":[
                {
                    "match":
                        {
                            "servicePathIdentifier": 55,
                            "serviceIndex": SIZE-i,
                            "dstAddr":"10.1.2.3"
                        }
                    ,
                    "action_params":
                        {
                            "prime": p,
                            "secretShare": int(y1[i]),
                            "publicPol": int(y2[i]),
                            "lpc": int(lpc[i]),
                            "upstreamMask": int(opot_masks[i],16),
                            "downstreamMask": int(opot_masks[i-1],16),
                            "magic_M": magic.M,
                            "magic_a": magic.a,
                            "magic_s": magic.s
                        }
                    
                },
                {
                    "match":
                        {
                            "servicePathIdentifier": 23,
                            "serviceIndex": i+1,
                            "dstAddr":"10.1.1.3"
                        }
                    ,
                    "action_params":
                        {
                            "prime": p,
                            "secretShare": int(y1[SIZE-1-i]),
                            "publicPol": int(y2[SIZE-1-i]),
                            "lpc": int(lpc[SIZE-1-i]),
                            "upstreamMask": int(opot_masks[len(opot_masks)-i],16),
                            "downstreamMask": int(opot_masks[len(opot_masks)-i-1],16),
                            "magic_M": magic.M,
                            "magic_a": magic.a,
                            "magic_s": magic.s
                        }
                    
                }
            ],
            "pot_egress_rules": [

            ],
            "metrics_rules":[
                {
                    "action_params":
                        {
                            "srcAddr":f"02:42:0a:00:00:{(i+11):02x}",
                            "dstAddr":"02:42:0a:00:00:0a",
                            "port": 3,
                            "ipSrcAddr":f"10.0.0.{i+11}",
                            "ipDstAddr":"10.0.0.10"
                        }
                    
                }
            ],
            "clone_rules":[
                {
                    "match":
                    {
                        "dstAddr":"10.1.1.3",
                        "prefix_len": 32,
                        "ingress_port": 2
                    } 
                },
                {
                    "match":
                    {
                        "dstAddr":"10.1.2.3",
                        "prefix_len": 32,
                        "ingress_port": 1
                    } 
                }
            ]
        }
    )

with open("config/switches.json", "w") as archivo:
    json.dump(datos, archivo, indent=4)

#Build keys file for secure parameter transmission

keys = { 
    "keys": ["keys/ca.crt","keys/client.crt","keys/client.key"]
}

with open("config/keys.json", "w") as archivo:
    json.dump(keys, archivo, indent=4)