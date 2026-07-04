variable "project_id" {
  type        = string
  description = "The Google Cloud Project ID where resources will be deployed."
}

variable "region" {
  type        = string
  description = "The target GCP region for all container services and metadata."
  default     = "us-central1"
}

variable "gemini_model" {
  type        = string
  description = "The Gemini model version to use for the AI SRE Agent."
  default     = "gemini-2.5-flash"
}
