import logging
import os
from typing import Dict, Any

from llama_cpp import Llama

from app.config import settings
from app.schemas import ParsedResult

logger = logging.getLogger(__name__)

class LLMParser:
    def __init__(self, model_path: str):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")

        self.llm = Llama(
            model_path=model_path,
            n_ctx=settings.N_CTX,
            n_threads=settings.N_THREADS,
            n_batch=settings.N_BATCH,
            use_mmap=settings.USE_MMAP,
            n_gpu_layers=settings.N_GPU_LAYERS,
            verbose=False,
        )

    def _build_prompt(self, title: str, remaining_text: str) -> str:
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are an expert at parsing metadata from file names. Your task is to identify the primary movie or series name from a noisy string. Provide only the cleaned name. Do not explain.

Examples:
- Input: "The.Boys.S01.COMPLETE.REPACK.2160p.AMZN.WEB-DL.DDP5.1.HEVC-NTb"
  Output: The Boys
- Input: "Oppenheimer.2023.1080p.BluRay.x264-YTS"
  Output: Oppenheimer
- Input: "Stranger Things 2016 S04E01E02 MULTi 1080p NF WEBRip x265-T4D"
  Output: Stranger Things
- Input: "The.Shawshank.Redemption.1994.INTERNAL.1080p.BluRay.x264-MARS"
  Output: The Shawshank Redemption<|eot_id|><|start_header_id|>user<|end_header_id|>
Analyze the following partial torrent title and extract the clean series or movie name.
Original Title: "{title}"
Remaining Text: "{remaining_text}"<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
        return prompt

    def refine_with_llm(self, parsed_data: Dict[str, Any], remaining_text: str, original_title: str) -> ParsedResult:
        """
        Uses the LLM to fill in gaps, primarily the main title.
        """
        result = ParsedResult(**parsed_data, raw=original_title)
        
        # If remaining text is very short or looks good, just use it.
        if len(remaining_text.split()) < 7 and not any(char.isdigit() for char in remaining_text):
            result.title = remaining_text.strip()
            result.confidence = min(result.confidence + 0.25, 1.0)
            result.notes = "Title derived from simple heuristics."
            return result

        # Otherwise, use the LLM
        prompt = self._build_prompt(original_title, remaining_text)
        
        try:
            output = self.llm(
                prompt,
                max_tokens=50,
                stop=["<|eot_id|>"],
                echo=False,
                temperature=0.0,
            )
            llm_title = output['choices'][0]['text'].strip()

            if llm_title:
                result.title = llm_title
                result.confidence = min(result.confidence + 0.3, 1.0) # Boost confidence
                result.notes = "Title identified by LLM."
            else:
                # Fallback if LLM gives empty response
                result.title = remaining_text.strip()
                result.notes = "LLM failed to provide a title, using fallback."

        except Exception as e:
            logger.error(f"LLM inference failed: {e}", exc_info=True)
            result.title = remaining_text.strip()
            result.notes = f"LLM inference error, using regex fallback. Error: {e}"

        return result
