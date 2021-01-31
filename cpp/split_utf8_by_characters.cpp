#include <stdio.h>
#include <iostream>
#include <vector>

std::vector<std::string> split_to_chars(const std::string& inp)
{
    std::string tmp;
    int8_t extra = 0;
    std::vector<std::string> out;
    for (int i = 0; i < inp.length(); i++)
    {
        uint8_t c = inp.at(i);
        if      ((c & 0b10000000) == 0b00000000) extra = 0;
        else if ((c & 0b11100000) == 0b11000000) extra = 1;
        else if ((c & 0b11110000) == 0b11100000) extra = 2;
        else if ((c & 0b11111000) == 0b11110000) extra = 3;
        tmp += c;
        while (extra--) tmp += inp.at(++i);
        out.push_back(tmp);
        tmp.clear();
    }
    return out;
}

int main(int argc, char* argv[])
{
    std::string s = "Привет, говно! こんにちはたわごと！ 안녕 젠장!";
    std::vector<std::string> out = split_to_chars(s);
    for (auto p : out)
        std::cout << p << " ";
    std::cout << std::endl;
    return 0;
}
