
import google.generativeai as genai
from typing import Dict, List, Optional
import os
import logging
from datetime import datetime
try:
    from src.config import get_secret
except ImportError:
    from config import get_secret

class LinkedInBlogGenerator:
    def __init__(self):
        self.api_key = get_secret('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API Key not found. Please set GOOGLE_API_KEY in .env file")
        
        
        genai.configure(api_key=self.api_key)
        
        
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("LinkedIn Blog Generator initialized successfully")
    
    def generate_blog_post(self, 
                          topic: str, 
                          tone: str = "professional",
                          length: str = "medium",
                          target_audience: str = "professionals",
                          include_hashtags: bool = True,
                          include_call_to_action: bool = True) -> Dict[str, str]:
        """
        Generate a LinkedIn blog post on a given topic.
        
        Args:
            topic (str): The main topic/theme for the blog post
            tone (str): Tone of the blog (professional, casual, inspirational, etc.)
            length (str): Length of the blog (short, medium, long)
            target_audience (str): Target audience description
            include_hashtags (bool): Whether to include hashtags
            include_call_to_action (bool): Whether to include a call to action
            
        Returns:
            Dict[str, str]: Generated blog post with title, content, hashtags, etc.
        """
        try:
            
            prompt = self._create_blog_prompt(
                topic=topic,
                tone=tone,
                length=length,
                target_audience=target_audience,
                include_hashtags=include_hashtags,
                include_call_to_action=include_call_to_action
            )
            
            self.logger.info(f"Generating blog post for topic: {topic}")
            
            
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        candidate_count=1,
                        max_output_tokens=2048,
                        temperature=0.7,
                    )
                )
                
                if not response.text:
                    raise Exception("No content generated from Google AI")
                
                
                blog_data = self._parse_blog_response(response.text)
                
                
                blog_data['generated_at'] = datetime.now().isoformat()
                blog_data['topic'] = topic
                blog_data['tone'] = tone
                blog_data['length'] = length
                
                self.logger.info("Blog post generated successfully")
                return blog_data
                
            except Exception as api_error:
                error_message = str(api_error).lower()
                
                if "quota" in error_message or "exceeded" in error_message or "limit" in error_message:
                    raise Exception(
                        "🚨 API Quota Exceeded!\n\n"
                        "Your Google AI (Gemini) free tier quota has been reached.\n\n"
                        "Solutions:\n"
                        "1. Wait for quota reset (usually 24 hours)\n"
                        "2. Upgrade to paid Google AI plan\n"
                        "3. Check your API usage at https://makersuite.google.com\n"
                        "4. Try again later with shorter content length\n\n"
                        f"Original error: {api_error}"
                    )
                elif "rate" in error_message:
                    raise Exception(
                        "🚨 Rate Limit Exceeded!\n\n"
                        "You're making requests too quickly.\n\n"
                        "Solutions:\n"
                        "1. Wait 60 seconds before trying again\n"
                        "2. Reduce frequency of blog generation\n\n"
                        f"Original error: {api_error}"
                    )
                else:
                    raise Exception(f"Google AI API Error: {api_error}")
            
        except Exception as e:
            self.logger.error(f"Error generating blog post: {str(e)}")
            raise
    
    def _create_blog_prompt(self, topic: str, tone: str, length: str, 
                           target_audience: str, include_hashtags: bool, 
                           include_call_to_action: bool) -> str:
        """
        Create a detailed prompt for blog generation.
        """
        length_guidelines = {
            "short": "150-300 words",
            "medium": "400-600 words", 
            "long": "700-1000 words"
        }
        
        prompt = f"""
        Create a professional LinkedIn blog post with the following specifications:

        Topic: {topic}
        Tone: {tone}
        Length: {length_guidelines.get(length, "400-600 words")}
        Target Audience: {target_audience}

        IMPORTANT FORMATTING GUIDELINES:
        - Use clean, professional text WITHOUT asterisks (*) for emphasis
        - DO NOT use emojis in the main content
        - Use proper paragraphs with clear line breaks
        - Write in a conversational yet professional style
        - Focus on valuable insights and actionable advice
        - Avoid excessive formatting symbols or decorative elements
        - Keep the {tone} tone throughout

        CONTENT REQUIREMENTS:
        1. Create an engaging, professional title (no emojis)
        2. Write a compelling opening paragraph
        3. Include 2-3 main points with practical insights
        4. Use clear, readable formatting with proper paragraphs
        5. Make it valuable and shareable for {target_audience}
        
        {"6. Include 5-8 relevant hashtags (hashtags only, no decorative elements)" if include_hashtags else ""}
        {"7. End with a professional call-to-action that encourages meaningful engagement" if include_call_to_action else ""}

        FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:
        TITLE: [Clean professional title here]
        
        CONTENT: [Main blog post content in clear paragraphs, no asterisks or emojis]
        
        {"HASHTAGS: [Only hashtags, separated by spaces]" if include_hashtags else ""}
        
        {"CALL_TO_ACTION: [Professional call to action]" if include_call_to_action else ""}

        Remember: Focus on professional, clean content that provides real value without unnecessary formatting.
        """
        
        return prompt
    
    def _parse_blog_response(self, response_text: str) -> Dict[str, str]:
        """
        Parse the AI response into structured blog data.
        """
        blog_data = {
            'title': '',
            'content': '',
            'hashtags': '',
            'call_to_action': '',
            'full_post': response_text
        }
        
        lines = response_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('TITLE:'):
                current_section = 'title'
                blog_data['title'] = line.replace('TITLE:', '').strip()
            elif line.startswith('CONTENT:'):
                current_section = 'content'
                blog_data['content'] = line.replace('CONTENT:', '').strip()
            elif line.startswith('HASHTAGS:'):
                current_section = 'hashtags'
                blog_data['hashtags'] = line.replace('HASHTAGS:', '').strip()
            elif line.startswith('CALL_TO_ACTION:'):
                current_section = 'call_to_action'
                blog_data['call_to_action'] = line.replace('CALL_TO_ACTION:', '').strip()
            elif current_section and line:
                # Continue adding to the current section
                if blog_data[current_section]:
                    blog_data[current_section] += '\n' + line
                else:
                    blog_data[current_section] = line
        
        # Clean the content to ensure professional formatting
        blog_data = self._clean_content(blog_data)
        
        return blog_data
    
    def _clean_content(self, blog_data: Dict[str, str]) -> Dict[str, str]:
        """
        Clean the generated content to ensure professional formatting.
        """
        import re
        
        # Clean title - remove excessive formatting
        if blog_data['title']:
            blog_data['title'] = re.sub(r'\*+', '', blog_data['title'])  # Remove asterisks
            blog_data['title'] = re.sub(r'[🎯📝💡🚀✨🔥💪🌟📈⭐️🎪🎭🎨🎬🎤🎼🎵🎶🎸🎺🎻🥳🤝👍💯]', '', blog_data['title'])  # Remove common emojis
            blog_data['title'] = blog_data['title'].strip()
        
        # Clean content - remove excessive formatting and emojis
        if blog_data['content']:
            content = blog_data['content']
            # Remove asterisks used for emphasis
            content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)  # Remove **bold**
            content = re.sub(r'\*([^*]+)\*', r'\1', content)      # Remove *italic*
            content = re.sub(r'\*+', '', content)                # Remove remaining asterisks
            
            # Remove emojis from content (keep it professional)
            content = re.sub(r'[🎯📝💡🚀✨🔥💪🌟📈⭐️🎪🎭🎨🎬🎤🎼🎵🎶🎸🎺🎻🥳🤝👍💯🌍🌎🌏🔮🎊🎉🎈🎀🎁🏆🥇🥈🥉🏅🎖️🏵️🎗️]', '', content)
            
            # Clean up multiple line breaks
            content = re.sub(r'\n{3,}', '\n\n', content)
            
            # Remove bullet points and formatting symbols
            content = re.sub(r'^[•▪▫◦‣⁃]\s*', '', content, flags=re.MULTILINE)
            content = re.sub(r'^[-*]\s+', '', content, flags=re.MULTILINE)
            
            blog_data['content'] = content.strip()
        
        # Clean hashtags - keep only actual hashtags
        if blog_data['hashtags']:
            hashtags = blog_data['hashtags']
            # Remove emojis from hashtags
            hashtags = re.sub(r'[🎯📝💡🚀✨🔥💪🌟📈⭐️🎪🎭🎨🎬🎤🎼🎵🎶🎸🎺🎻🥳🤝👍💯]', '', hashtags)
            # Ensure hashtags start with #
            hashtags = re.sub(r'(?<!\#)\b([A-Za-z][A-Za-z0-9_]*)', r'#\1', hashtags)
            blog_data['hashtags'] = hashtags.strip()
        
        # Clean call to action
        if blog_data['call_to_action']:
            cta = blog_data['call_to_action']
            # Remove emojis from CTA
            cta = re.sub(r'[🎯📝💡🚀✨🔥💪🌟📈⭐️🎪🎭🎨🎬🎤🎼🎵🎶🎸🎺🎻🥳🤝👍💯]', '', cta)
            cta = re.sub(r'\*+', '', cta)  # Remove asterisks
            blog_data['call_to_action'] = cta.strip()
        
        return blog_data
    
    def generate_multiple_posts(self, topics: List[str], **kwargs) -> List[Dict[str, str]]:
        """
        Generate multiple blog posts for different topics.
        
        Args:
            topics (List[str]): List of topics to generate posts for
            **kwargs: Additional parameters for blog generation
            
        Returns:
            List[Dict[str, str]]: List of generated blog posts
        """
        blog_posts = []
        
        for topic in topics:
            try:
                post = self.generate_blog_post(topic=topic, **kwargs)
                blog_posts.append(post)
                self.logger.info(f"Generated post for topic: {topic}")
            except Exception as e:
                self.logger.error(f"Failed to generate post for topic '{topic}': {str(e)}")
                continue
        
        return blog_posts
    
    def get_topic_suggestions(self, industry: str, keywords: List[str] = None) -> List[str]:
        """
        Generate topic suggestions for blog posts based on industry and keywords.
        
        Args:
            industry (str): The industry or field
            keywords (List[str]): Optional keywords to include
            
        Returns:
            List[str]: List of suggested topics
        """
        try:
            keywords_str = ", ".join(keywords) if keywords else "general topics"
            
            prompt = f"""
            Suggest 10 trending and engaging LinkedIn blog post topics for the {industry} industry.
            
            Consider these keywords: {keywords_str}
            
            Make sure the topics are:
            1. Relevant to current industry trends
            2. Engaging and likely to get good engagement on LinkedIn
            3. Valuable to professionals in this field
            4. Actionable and practical
            
            Format your response as a numbered list:
            1. Topic 1
            2. Topic 2
            ...etc
            """
            
            response = self.model.generate_content(prompt)
            
            # Extract topics from response
            topics = []
            lines = response.text.split('\n')
            for line in lines:
                line = line.strip()
                if line and any(line.startswith(f"{i}.") for i in range(1, 11)):
                    topic = line.split('.', 1)[1].strip() if '.' in line else line
                    topics.append(topic)
            
            return topics
            
        except Exception as e:
            self.logger.error(f"Error generating topic suggestions: {str(e)}")
            return []


if __name__ == "__main__":
    # Example usage
    try:
        # Initialize the generator
        generator = LinkedInBlogGenerator()
        
        # Generate a blog post
        blog_post = generator.generate_blog_post(
            topic="The Future of AI in Business",
            tone="professional",
            length="medium",
            target_audience="business professionals and entrepreneurs"
        )
        
        print("Generated Blog Post:")
        print(f"Title: {blog_post['title']}")
        print(f"\nContent:\n{blog_post['content']}")
        print(f"\nHashtags: {blog_post['hashtags']}")
        print(f"\nCall to Action: {blog_post['call_to_action']}")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure to set your GOOGLE_API_KEY in the .env file")