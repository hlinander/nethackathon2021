#include "common.h"
#include "llama.h"

#include <ctime>

#if defined(_MSC_VER)
#pragma warning(disable: 4244 4267) // possible loss of data
#endif

static std::vector<std::string> split_lines(const std::string & s) {
    std::string line;
    std::vector<std::string> lines;
    std::stringstream ss(s);
    while (std::getline(ss, line)) {
        lines.push_back(line);
    }
    return lines;
}

static std::vector<std::string> split_lines_pp(const std::string& s) {
    const size_t maxLineLength = 500;
    std::string line, current;
    std::vector<std::string> lines, finalLines;
    std::stringstream ss(s);

    // First, split the input string by new lines
    while (std::getline(ss, line)) {
        // If a line is longer than 2048, split it further
        while (line.length() > maxLineLength) {
            lines.push_back(line.substr(0, maxLineLength));
            line = line.substr(maxLineLength);
        }
        // Push the last piece or any line shorter than 2048
        if (!line.empty()) {
            lines.push_back(line);
        }
    }

    // Now, merge lines that are shorter than 2048 characters
    for (const auto& smallLine : lines) {
        if (!current.empty() && current.length() + smallLine.length() + 3 > maxLineLength) {
            finalLines.push_back(current);
            current.clear();
        }
        if (current.empty()) {
            current = smallLine;
        } else {
            current += ". " + smallLine;
        }
    }

    // Don't forget to add the last constructed line if not empty
    if (!current.empty()) {
        finalLines.push_back(current);
    }

    return finalLines;
}

static void batch_add_seq(llama_batch & batch, const std::vector<int32_t> & tokens, int seq_id) {
    for (size_t i = 0; i < tokens.size(); i++) {
        llama_batch_add(batch, tokens[i], i, { seq_id }, i == tokens.size() - 1);
    }
}

static void batch_decode(llama_context * ctx, llama_batch & batch, float * output, int n_seq, int n_embd) {
    // clear previous kv_cache values (irrelevant for embeddings)
    llama_kv_cache_clear(ctx);

    // run model
    fprintf(stderr, "%s: n_tokens = %d, n_seq = %d\n", __func__, batch.n_tokens, n_seq);
    if (llama_decode(ctx, batch) < 0) {
        fprintf(stderr, "%s : failed to decode\n", __func__);
    }

    for (int i = 0; i < batch.n_tokens; i++) {
        if (!batch.logits[i]) {
            continue;
        }

        // try to get sequence embeddings - supported only when pooling_type is not NONE
        const float * embd = llama_get_embeddings_seq(ctx, batch.seq_id[i][0]);
        if (embd == NULL) {
            embd = llama_get_embeddings_ith(ctx, i);
            if (embd == NULL) {
                fprintf(stderr, "%s: failed to get embeddings for token %d\n", __func__, i);
                continue;
            }
        }

        float * out = output + batch.seq_id[i][0] * n_embd;
        llama_embd_normalize(embd, out, n_embd);
    }
}

void write_embeddings(int index, int n_prompts, float *emb, int n_embd, std::vector<std::string> &prompts, int prompt_head, std::string out_prefix) {
    // std::string out_file = "embeddings_out_" + std::to_string(index)
    char buffer[200];
    snprintf(buffer, sizeof(buffer), "%s_%0*d.bin", out_prefix.c_str(), 5, index);
    FILE *embed_out = fopen(buffer, "wb");
    fwrite(&n_embd, sizeof(int), 1, embed_out);
    for (int j = 0; j < n_prompts; j++) {
        // fprintf(embed_out, "%s", )
        fwrite(&emb[j * n_embd], sizeof(float), n_embd, embed_out);
        auto prompt_length = static_cast<uint32_t>(prompts[prompt_head + j].size()); // Cast size to uint32_t
        fwrite(&prompt_length, sizeof(prompt_length), 1, embed_out);
        fwrite(prompts[prompt_head + j].data(), sizeof(char), prompts[prompt_head + j].size(), embed_out);
        // int prompt_length = prompts[j].
        // fwrite()
        // fprintf(stdout, "embedding %d: ", j);
        // for (int i = 0; i < (n_prompts > 1 ? std::min(16, n_embd) : n_embd); i++) {
            // fprintf(stdout, "%9.6f ", emb[j * n_embd + i]);
        // }
        // fprintf(stdout, "\n");
    }
    fclose(embed_out);
    
}

int main(int argc, char ** argv) {
    gpt_params params;

    if (!gpt_params_parse(argc, argv, params)) {
        return 1;
    }

    params.embedding = true;
    // For non-causal models, batch size must be equal to ubatch size
    params.n_ubatch = params.n_batch;

    print_build_info();

    if (params.seed == LLAMA_DEFAULT_SEED) {
        params.seed = time(NULL);
    }

    fprintf(stderr, "%s: seed  = %u\n", __func__, params.seed);

    std::mt19937 rng(params.seed);
    if (params.random_prompt) {
        params.prompt = gpt_random_prompt(rng);
    }

    llama_backend_init();
    llama_numa_init(params.numa);

    llama_model * model;
    llama_context * ctx;

    // load the model
    std::tie(model, ctx) = llama_init_from_gpt_params(params);
    if (model == NULL) {
        fprintf(stderr, "%s: error: unable to load model\n", __func__);
        return 1;
    }

    const int n_ctx_train = llama_n_ctx_train(model);
    const int n_ctx = llama_n_ctx(ctx);
    // fprintf(stdout, "%d", ctx.n)

    if (n_ctx > n_ctx_train) {
        fprintf(stderr, "%s: warning: model was trained on only %d context tokens (%d specified)\n",
                __func__, n_ctx_train, n_ctx);
    }

    // print system information
    {
        fprintf(stderr, "\n");
        fprintf(stderr, "%s\n", get_system_info(params).c_str());
    }

    // split the prompt into lines
    std::vector<std::string> prompts = split_lines_pp(params.prompt);
    // std::cout << "PROMPTS:" << std::endl;
    // for(auto prompt: prompts) {
        // std::cout << prompt << std::endl;
    // }

    // max batch size
    const uint64_t n_batch = params.n_batch;
    GGML_ASSERT(params.n_batch >= params.n_ctx);

    // tokenize the prompts and trim
    std::vector<std::vector<int32_t>> inputs;
    for (const auto & prompt : prompts) {
        auto inp = ::llama_tokenize(ctx, prompt, true, false);
        if (inp.size() > n_batch) {
            fprintf(stderr, "%s: error: number of tokens in input line (%lld) exceeds batch size (%lld), increase batch size and re-run\n",
                    __func__, (long long int) inp.size(), (long long int) n_batch);
            return 1;
        }
        inputs.push_back(inp);
    }

    // add eos if not present
    for (auto & inp : inputs) {
        if (inp.empty() || inp.back() != llama_token_eos(model)) {
            inp.push_back(llama_token_eos(model));
        }
    }

    // tokenization stats
    if (params.verbose_prompt) {
        for (int i = 0; i < (int) inputs.size(); i++) {
            fprintf(stderr, "%s: prompt %d: '%s'\n", __func__, i, prompts[i].c_str());
            fprintf(stderr, "%s: number of tokens in prompt = %zu\n", __func__, inputs[i].size());
            for (int j = 0; j < (int) inputs[i].size(); j++) {
                fprintf(stderr, "%6d -> '%s'\n", inputs[i][j], llama_token_to_piece(ctx, inputs[i][j]).c_str());
            }
            fprintf(stderr, "\n\n");
        }
    }

    // initialize batch
    const int n_prompts = prompts.size();
    struct llama_batch batch = llama_batch_init(n_batch, 0, 1);

    // allocate output
    const int n_embd = llama_n_embd(model);
    std::vector<float> embeddings(n_prompts * n_embd, 0);
    float * emb = embeddings.data();

    // break into batches
    int p = 0; // number of prompts processed already
    int s = 0; // number of prompts in current batch
    int embed_out_index = 0;
    int embed_out_head = 0;
    for (int k = 0; k < n_prompts; k++) {
        // clamp to n_batch tokens
        auto & inp = inputs[k];

        const uint64_t n_toks = inp.size();

        // encode if at capacity
        if (batch.n_tokens + n_toks > n_batch) {
            float * out = emb + p * n_embd;
            batch_decode(ctx, batch, out, s, n_embd);
            llama_batch_clear(batch);
            p += s;
            s = 0;
            if (p - embed_out_head > 20) {
                write_embeddings(embed_out_index, p - embed_out_head, emb + embed_out_head * n_embd, n_embd, prompts, embed_out_head, params.prompt_file);
                embed_out_index++;
                embed_out_head = p;
            }
        }

        // add to batch
        batch_add_seq(batch, inp, s);
        s += 1;

        // if(k % 100 == 0) {
            // fprintf(stdout, ".");
        // }
    }

    // final batch
    float * out = emb + p * n_embd;
    batch_decode(ctx, batch, out, s, n_embd);
    write_embeddings(embed_out_index, s, emb + embed_out_head * n_embd, n_embd, prompts, embed_out_head, params.prompt_file);

    // print the first part of the embeddings or for a single prompt, the full embedding
    // fprintf(stdout, "\n Writing embedding... \n");
    // fprintf(stdout, "\n");
    for (int i = 0; i < n_embd; i++) {
         fprintf(stdout, "%9.6f, ", emb[i]);
    }

    // print cosine similarity matrix
    if (n_prompts > 1) {
        fprintf(stdout, "\n");
        printf("cosine similarity matrix:\n\n");
        for (int i = 0; i < n_prompts; i++) {
            for (int j = 0; j < n_prompts; j++) {
                float sim = llama_embd_similarity_cos(emb + i * n_embd, emb + j * n_embd, n_embd);
                fprintf(stdout, "%6.2f ", sim);
            }
            fprintf(stdout, "\n");
        }
    }

    // clean up
    // llama_print_timings(ctx);
    llama_free(ctx);
    llama_free_model(model);
    llama_backend_free();

    return 0;
}
