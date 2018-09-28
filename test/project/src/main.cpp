#include "library-two.h"

#include "template.ipp"

using namespace std;

#include <iostream>

int main(int argc, char *argv[])
{
    auto instance = two::Class();
    instance.call(TemplateClass<string>("hello"));
}
