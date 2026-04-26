
def build_dfb_wreg0(col):
    return col << 6


def build_dfbchn_wreg0(chn, state):
    return (chn << 6) | state


def build_dfbchn_wreg1(a2d_lockpt):
    return (1 << 25) | a2d_lockpt


def build_clk_wreg1(CLKstate, notCLKstate):
    return (1 << 25) | (notCLKstate << 24) | (CLKstate << 23)


def build_clk_wreg2(lsync_minus1):
    return (2 << 25) | lsync_minus1


def build_dfbchn_wreg2(triA, triB, d2a_A):
    return (2 << 25) | (triA << 16) | (triB << 17) | d2a_A


def build_dfbchn_wreg3(FBA, FBB, ARL, P, I):
    wreg = 3 << 25
    wreg |= int(FBA) << 24
    wreg |= int(FBB) << 23
    wreg |= int(ARL) << 21
    wreg |= (int(P) & 0x3ff) << 10
    return wreg | (int(I) & 0x3ff)


def build_dfb_wreg4(wreg4, GR):
    return (wreg4 & 0xFFF7FFF) | (GR << 15)


def build_dfbchn_wreg5(d2a_B, SM):
    return (5 << 25) | (d2a_B << 11) | SM


def build_dfbclk_wreg6(PS, dfbclk_XPT, CLK, NSAMP):
    return (6 << 25) | (PS << 24) | (dfbclk_XPT << 21) | (CLK << 20) | NSAMP


def build_dfbx2_wreg6(PS, dfbx2_XPT, NSAMP):
    return (6 << 25) | (PS << 24) | (dfbx2_XPT << 21) | NSAMP


def build_clk_wreg7(seqln):
    return (7 << 25) | (seqln << 8)


def build_dfb_wreg7(LED, ST, prop_delay, dfb_delay, seqln, SETT):
    return (7 << 25) | (LED << 23) | (ST << 22) | (prop_delay << 18) \
        | (dfb_delay << 14) | (seqln << 8) | SETT


