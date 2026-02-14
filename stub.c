// Empty stub to help with linking
// This file ensures the C runtime library is properly linked
#include <stdio.h>

// Force linking of scanf and printf
void force_link() {
    scanf("");
    printf("");
}
