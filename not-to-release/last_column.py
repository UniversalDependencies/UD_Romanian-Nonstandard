# Transferă ultima coloană dintr-un fișier conllu în altul aliniind tokenii.
import sys
import argparse


def read_conllu_sentences(path):
    sentences = []
    current = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line == "":
                if current:
                    sentences.append(current)
                    current = []
            else:
                current.append(line)
        if current:
            sentences.append(current)

    return sentences


def extract_sent_id(sentence):
    for line in sentence:
        if line.startswith("# sent_id"):
            return line.split("=", 1)[1].strip()
    return None


def split_sentence(sentence):
    comments = []
    tokens = []

    for line in sentence:
        if line.startswith("#"):
            comments.append(line)
        else:
            tokens.append(line)

    return comments, tokens


def parse_token(line):
    cols = line.split("\t")
    if len(cols) < 10:
        return None
    return cols


def is_real_token_id(tok_id):
    # Skip multiword tokens (e.g., 1-2) but keep empty nodes (e.g., 3.1)
    return "-" not in tok_id


def transfer(old_path, new_path, output_path):
    old_sentences = read_conllu_sentences(old_path)
    new_sentences = read_conllu_sentences(new_path)

    # Index OLD by sent_id
    old_dict = {}
    
    for sent in old_sentences:
        sid = extract_sent_id(sent)
        
        if sid is None:
            raise ValueError("Missing # sent_id in OLD file.")
        # end if
        
        old_dict[sid] = sent

    with open(output_path, "w", encoding="utf-8") as out:
        for new_sent in new_sentences:
            sid = extract_sent_id(new_sent)
            
            if sid is None:
                raise ValueError("Missing # sent_id in NEW file.")
            # end if

            if sid not in old_dict:
                print(f"Sentence ID {sid} not found in OLD file.", file=sys.stderr, flush=True)
                continue
            # end if

            old_sent = old_dict[sid]

            old_comments, old_tokens = split_sentence(old_sent)
            _, new_tokens = split_sentence(new_sent)

            # Parse tokens (filter malformed + multiword lines)
            old_parsed = [parse_token(t) for t in old_tokens]
            old_parsed = [t for t in old_parsed if t and is_real_token_id(t[0])]

            new_parsed = [parse_token(t) for t in new_tokens]
            new_parsed = [t for t in new_parsed if t and is_real_token_id(t[0])]

            # Greedy alignment by FORM (column 2)
            i, j = 0, 0
            alignment = {}  # new_index -> old_index

            while i < len(old_parsed) and j < len(new_parsed):
                old_form = old_parsed[i][1]
                new_form = new_parsed[j][1]

                if old_form == new_form:
                    alignment[j] = i
                    i += 1
                    j += 1
                else:
                    # try to recover from tokenization differences
                    # advance the shorter "side"
                    if len(old_form) <= len(new_form):
                        i += 1
                    else:
                        j += 1

            # Write OLD comments
            for c in old_comments:
                out.write(c + "\n")

            # Reconstruct NEW tokens, injecting MISC when aligned
            real_j = 0  # index in new_parsed

            for line in new_tokens:
                cols = parse_token(line)

                if not cols or not is_real_token_id(cols[0]):
                    out.write(line + "\n")
                    continue

                if real_j in alignment:
                    old_idx = alignment[real_j]
                    cols[9] = old_parsed[old_idx][9]

                out.write("\t".join(cols) + "\n")
                real_j += 1

            out.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transfer MISC column and comments from OLD to NEW CoNLL-U, aligning by token FORM."
    )
    parser.add_argument("old", help="Path to OLD.conllu")
    parser.add_argument("new", help="Path to NEW.conllu")
    parser.add_argument(
        "-o", "--output",
        default="MERGED.conllu",
        help="Output file (default: MERGED.conllu)"
    )

    args = parser.parse_args()
    transfer(args.old, args.new, args.output)
    