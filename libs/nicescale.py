# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


import math

class NiceScale:

    def __init__(self, minval, maxval, maxticks=10, forcezero=False, zerothresh=0.2):
        self.minval = minval if minval else 0
        self.maxval = maxval if maxval else 0
        self.maxticks = maxticks
        self.zerothresh = zerothresh
        self.forcezero = forcezero
        self.calculate()
        
    #
    # Calculate and update values for tick spacing and nice
    # minimum and maximum data points on the axis.
    #
    def calculate(self):
        if (self.forcezero or (self.minval > 0) and 
                (self.maxval > 0) and 
                ((float(self.maxval - self.minval) / self.maxval) > self.zerothresh)):
            self.minval = 0

        vrange = self.maxval - self.minval
        if vrange == 0:
            self.tickSpacing = 1
            self.niceMin = 0
            self.niceMax = 1
            self.numTicks = 1
        else:
            valrange = self.niceNum(vrange, False)
            self.tickSpacing = self.niceNum(float(valrange) / (self.maxticks - 1), True)
            self.niceMin = math.floor(self.minval / self.tickSpacing) * self.tickSpacing
            self.niceMax = math.ceil(self.maxval / self.tickSpacing) * self.tickSpacing
            self.numTicks = 1 + round((self.niceMax - self.niceMin) / self.tickSpacing)
        
    #
    # Returns a "nice" number approximately equal to range Rounds
    # the number if round = True Takes the ceiling if round = False.
    #
    # @param valrange the data range
    # @param round whether to round the result
    # @return a "nice" number to be used for the data range
    
    def niceNum(self, valrange, round):
        if valrange == 0:
            return 0

        exponent = math.floor(math.log10(valrange))
        fraction = valrange / math.pow(10, exponent)
        
        if (round):
            if (fraction < 1.5):
                niceFraction = 1
            elif (fraction < 3):
                niceFraction = 2
            elif (fraction < 7):
                niceFraction = 5
            else:
                niceFraction = 10
        else:
            if (fraction <= 1):
                niceFraction = 1
            elif (fraction <= 2):
                niceFraction = 2
            elif (fraction <= 5):
                niceFraction = 5
            else:
                niceFraction = 10
            
        return niceFraction * math.pow(10, exponent)
    
    def dump(self):
        a = []
        x = self.niceMin
        while x <= self.niceMax:
            a.append("%.4f" % x)
            x += self.tickSpacing
        print "(%.4f - %.4f @ %d) => %d [%s]" % (self.minval,
                                                 self.maxval,
                                                 self.maxticks, 
                                                 self.numTicks, 
                                                 ', '.join(a))

    
if __name__ == "__main__":
    def test(minval, maxval, maxticks=10):
        n = NiceScale(minval, maxval, maxticks)
        n.dump()
        
    #test(100,500)
    #test(100,500,5)
    #test(100,500,4)
    #test(92,156)
    #test(0.09,.9)
    #test(0.2, 0.28)
    #test(1, 19)
    test(0.101, 0.119)
