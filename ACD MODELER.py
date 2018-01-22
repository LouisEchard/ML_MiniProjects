import json
from pprint import pprint
import scipy.optimize as optimize
import pandas as pd
import numpy as np
from datetime import datetime
from enum import Enum

data = json.load(open('feeddata_10.json'))

def getBookContract(aStringNumberContract, aTypeOption):
    aContract = ''
    if aStringNumberContract == "000" and aTypeOption == "1":
        aContract = CONTRACTTYPE.FUTURE  # replace with enums
    elif aTypeOption == "2":
        aContract = CONTRACTTYPE.CALL
    elif aTypeOption == "3":
        aContract = CONTRACTTYPE.PUT
    else:
        print("error, Contract Type" + str(aStringNumberContract) + " , " + str(aTypeOption) + " not recognized")

    return aContract


class CONTRACTTYPE(Enum):
    UNSET = 0
    FUTURE = 1
    CALL = 2
    PUT = 3




def residualTotalModACD(params_, pqs_):
    check1 = []
    check2 = []

    # variables of Interest:
    errs = []
    psis = []
    xs = []
    volumeO = []
    volumeF = []
    TO = []
    TF = []

    p = pqs_[0]
    q = pqs_[1]
    r = pqs_[2]
    s = pqs_[3]

    alpha0 = params_[0]
    alphas = params_[1:p + 1]
    betas = params_[p + 1:q + p + 1]
    gammas = params_[q + p + 1:q + p + 1 + r]
    deltas = params_[q + p + r + 1:q + p + r + s + 1]

    initialized = False
    first = True
    for idx, tick in enumerate(data):

        myBook = tick["book"]

        if myBook[5] == '1' and tick['type'] == 'lastdone' and getBookContract(myBook[8:11],
                                                                               myBook[3]) is CONTRACTTYPE.FUTURE:
            volumeF.append(tick['volume'])
            TF.append(datetime.utcfromtimestamp(tick['received'] / 1000000))
        if myBook[5] == '1' and tick['type'] == 'lastdone' and getBookContract(myBook[8:11], myBook[
            3]) is CONTRACTTYPE.CALL and myBook[8:11] == '335':
            volumeO.append(tick['volume'])
            TO.append(datetime.utcfromtimestamp(tick['received'] / 1000000))

        if myBook[5] == '1' and tick['type'] == 'tick':  # let's forget about mini futures
            myContract = getBookContract(myBook[8:11], myBook[3])

            if myContract is CONTRACTTYPE.CALL and myBook[8:11] == '335':  # let's take a single option strike to see
                if len(xs) > p:
                    xs.pop(0)
                if len(psis) > q:
                    psis.pop(0)
                if len(volumeO) > r:
                    volumeO.pop(0)
                    TO.pop(0)
                if len(volumeF) > s:
                    volumeF.pop(0)
                    TF.pop(0)

                if initialized and not first:

                    # calculate alphas and betas parts
                    alphaSum = 0.0
                    betaSum = 0.0
                    gammaSum = 0.0
                    deltaSum = 0.0
                    for idx2, alpha in enumerate(alphas):
                        # print(xs)
                        alphaSum = alphaSum + alpha * xs[
                            idx2]  # doesn't matter if sum in reverse order, just means that alphas are in reverse order too
                    for idx2, beta in enumerate(betas):
                        # print(psis)
                        if len(psis) > idx2:
                            betaSum = betaSum + beta * psis[idx2]
                    for idx2, gamma in enumerate(gammas):
                        gammaSum = gammaSum + gamma * volumeO[idx2] * (
                        datetime.utcfromtimestamp(tick['received'] / 1000000) - TO[idx2]).microseconds / 1000
                    for idx2, delta in enumerate(deltas):
                        deltaSum = deltaSum + delta * volumeF[idx2] * (
                        datetime.utcfromtimestamp(tick['received'] / 1000000) - TF[idx2]).microseconds / 1000

                    expectedTime = alpha0 + alphaSum + betaSum + gammaSum + deltaSum  # expected time (psi)
                    psis.append(expectedTime)
                    xs.append((datetime.utcfromtimestamp(tick["created"] / 1000000) - myPastTime).microseconds / 1000)

                    errs.append((expectedTime - xs[p]) * (expectedTime - xs[p]))
                    check1.append(expectedTime)
                    check2.append(xs[p])

                elif first:
                    first = False
                else:
                    xs.append((datetime.utcfromtimestamp(tick["created"] / 1000000) - myPastTime).microseconds / 1000)
                    if len(xs) == p and len(volumeO) == r and len(volumeF) == s:
                        initialized = True

                myPastTime = datetime.utcfromtimestamp(tick["created"] / 1000000)

                # maintain right array size
                if len(xs) > p:
                    xs.pop(0)
                if len(psis) > q:
                    psis.pop(0)
                if len(volumeO) > r:
                    volumeO.pop(0)
                    TO.pop(0)
                if len(volumeF) > s:
                    volumeF.pop(0)
                    TF.pop(0)

                if idx > 200:
                    break
    # return errs,check1,check2
    return np.average(errs)





def main():


    # parameters:
    alpha0 = 0.0
    alphas = [1, 1, 1, 1, 1, 1]
    betas = [1, 1, 1, 1]
    gammas = [1, 1]
    deltas = [1, 1]
    params_ = [alpha0] + alphas + betas + gammas + deltas

    optimize.minimize(residualTotalModACD, params_, args=([len(alphas), len(betas), len(gammas), len(deltas)]),
                      method='COBYLA', options={'maxiter': 10000})


if __name__ == "__main__":
    main()