import sys

class BrainfuckInterpreter:
    def __init__(self):
        self.memory = [0] * 30000
        self.pointer = 0

    def run(self, code):
        output = ''
        loop_starts = []
        for i, c in enumerate(code):
            if c == '>':
                self.pointer += 1
            elif c == '<':
                self.pointer -= 1
            elif c == '+':
                self.memory[self.pointer] += 1
            elif c == '-':
                self.memory[self.pointer] -= 1
            elif c == '.':
                output += chr(self.memory[self.pointer])
            elif c == ',':
                self.memory[self.pointer] = ord(sys.stdin.read(1))
            elif c == '[':
                if self.memory[self.pointer] == 0:
                    loop_count = 1
                    while loop_count != 0:
                        i += 1
                        if code[i] == '[':
                            loop_count += 1
                        elif code[i] == ']':
                            loop_count -= 1
                else:
                    loop_starts.append(i)
            elif c == ']':
                if self.memory[self.pointer] != 0:
                    i = loop_starts[-1]
                else:
                    loop_starts.pop()
            else:
                continue
        return output

if __name__ == '__main__':
    bf = BrainfuckInterpreter()
    code = input('Enter Brainfuck code: ')
    output = bf.run(code)
    print('Output:', output)
