#!/usr/bin/env python3
"""
Script to update placeholder tips in Firebase with more article-specific content.
This addresses the issue where "No tips available" placeholders appear in the web interface.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Firebase collection names from environment variables
tips_collection = os.getenv("FIREBASE_COLLECTION_TIPS", "tips")
news_collection = os.getenv("FIREBASE_COLLECTION_NEWS", "news")

def update_placeholder_tips():
    """Update placeholder tips with article-specific content"""
    
    try:
        # Import Firebase helper functions
        from firebase_helper import initialize_firebase, find, find_one, update_one, close
        
        # Initialize Firebase
        firebase = initialize_firebase()
        if firebase is None:
            print("Error: Could not connect to Firebase Firestore")
            return False
        
        print(f"Connected to Firebase Firestore")
        
        # Find all articles
        articles = find(news_collection)
        print(f"Found {len(articles)} articles in collection: {news_collection}")
        
        updates_count = 0
        
        # Check each article for placeholder tips
        for article in articles:
            article_id = article.get("_id")
            if not article_id:
                continue
                
            # Get current tips for this article
            tips = find_one(tips_collection, {"article_id": article_id})
            
            # Check if tips exist and have a placeholder summary
            needs_update = True  # Force update for all tips to ensure uniqueness
            if not tips:
                print(f"No tips found for article: {article.get('title', 'Unknown')}")
            elif "tips" in tips and isinstance(tips["tips"], dict) and "summary" in tips["tips"]:
                # Check for placeholder indicators
                placeholder_indicators = [
                    "No tips available", 
                    "This is a placeholder", 
                    "basic security recommendations",
                    "should be aware of potential security implications"
                ]
                if any(indicator.lower() in tips["tips"]["summary"].lower() for indicator in placeholder_indicators):
                    print(f"Found placeholder tips for article: {article.get('title', 'Unknown')}")
                else:
                    print(f"Updating tips for article: {article.get('title', 'Unknown')}")
            
            if needs_update:
                # Create article-specific tips
                title = article.get('title', 'Unknown Title')
                content = article.get('description', '')
                
                # Extract security-related keywords and topics
                security_categories = {
                    "vulnerability": ["vulnerability", "cve", "exploit", "patch", "bug", "flaw", "weakness"],
                    "malware": ["malware", "virus", "trojan", "ransomware", "botnet", "backdoor", "worm"],
                    "phishing": ["phishing", "social engineering", "scam", "spam", "fraud", "impersonation"],
                    "data_breach": ["breach", "leak", "stolen data", "exposed data", "compromised"],
                    "network_security": ["network", "firewall", "router", "protocol", "vpn", "traffic"],
                    "authentication": ["password", "authentication", "credentials", "login", "mfa", "2fa"],
                    "encryption": ["encryption", "cryptography", "cipher", "encrypted", "decrypt"],
                    "zero_day": ["zero-day", "0day", "unpatched", "unknown vulnerability"],
                    "compliance": ["compliance", "regulation", "gdpr", "hipaa", "pci", "policy"],
                    "iot_security": ["iot", "smart device", "connected device", "smart home"],
                    "cloud_security": ["cloud", "aws", "azure", "gcp", "saas", "cloud storage"],
                    "mobile_security": ["mobile", "android", "ios", "smartphone", "app"]
                }
                
                # Match article content to security categories
                matched_categories = {}
                for category, keywords in security_categories.items():
                    # Count keyword matches in title and content
                    match_count = 0
                    for keyword in keywords:
                        if keyword.lower() in title.lower():
                            # Title matches are more important
                            match_count += 3
                        if content and keyword.lower() in content.lower():
                            match_count += 1
                    
                    if match_count > 0:
                        matched_categories[category] = match_count
                
                # Sort categories by match count
                top_categories = sorted(matched_categories.items(), key=lambda x: x[1], reverse=True)[:2]
                
                # Determine primary and secondary category 
                primary_category = top_categories[0][0] if top_categories else "general"
                secondary_category = top_categories[1][0] if len(top_categories) > 1 else None
                
                # Create category-specific tips
                category_tips = {
                    "vulnerability": {
                        "summary": "This article discusses critical vulnerability issues that could be exploited if left unaddressed. Organizations should prioritize applying security patches to mitigate potential risks.",
                        "dos": [
                            "Apply security patches immediately as they become available",
                            "Implement recommended workarounds if patches aren't yet available",
                            "Monitor vendor security bulletins for updates on these vulnerabilities",
                            "Run vulnerability scans regularly to identify affected systems"
                        ],
                        "donts": [
                            "Don't ignore critical vulnerability notifications related to your systems",
                            "Don't leave vulnerable systems exposed to the internet unnecessarily",
                            "Don't delay security updates for critical production systems",
                            "Don't run outdated software with known security vulnerabilities"
                        ]
                    },
                    "malware": {
                        "summary": "This article addresses malware threats that can compromise system security and data integrity. Organizations should implement robust malware protection measures.",
                        "dos": [
                            "Deploy comprehensive anti-malware solutions across all systems",
                            "Maintain offline backups of critical data to protect against ransomware",
                            "Scan all downloaded files before opening them",
                            "Implement application whitelisting where practical"
                        ],
                        "donts": [
                            "Don't open email attachments or click links from untrusted sources",
                            "Don't disable security software even temporarily",
                            "Don't pay ransoms if infected with ransomware - it encourages attackers",
                            "Don't run applications from unknown or untrusted sources"
                        ]
                    },
                    "phishing": {
                        "summary": "This article highlights phishing attack techniques that attempt to steal sensitive information through deception. Users should exercise caution with unexpected communications.",
                        "dos": [
                            "Verify sender identities before responding to requests for information",
                            "Inspect URLs carefully before clicking on links in emails or messages",
                            "Report suspected phishing attempts to your security team",
                            "Use multi-factor authentication for all important accounts"
                        ],
                        "donts": [
                            "Don't click on links in unsolicited emails, even if they appear legitimate",
                            "Don't provide personal or financial information in response to email requests",
                            "Don't rush decisions when pressured to act quickly by email or phone",
                            "Don't ignore warning signs like spelling errors or suspicious sender addresses"
                        ]
                    },
                    "data_breach": {
                        "summary": "This article discusses a data breach incident where sensitive information was compromised. Organizations should take immediate steps to protect affected users and prevent similar incidents.",
                        "dos": [
                            "Change passwords for any accounts mentioned in breach notifications",
                            "Monitor your accounts and credit reports for suspicious activity",
                            "Enable breach alerts and notifications for your accounts",
                            "Consider using a password manager to create and store unique credentials"
                        ],
                        "donts": [
                            "Don't ignore breach notifications related to your accounts or data",
                            "Don't reuse passwords across multiple sites or services",
                            "Don't share sensitive personal information unnecessarily",
                            "Don't use easily guessable security questions for account recovery"
                        ]
                    },
                    "network_security": {
                        "summary": "This article covers network security vulnerabilities that could allow unauthorized access. Network administrators should review their security configurations to address these issues.",
                        "dos": [
                            "Implement network segmentation to contain potential breaches",
                            "Configure firewalls with strict rules following the principle of least privilege",
                            "Enable encryption for all sensitive network traffic",
                            "Regularly audit network devices and configurations for security issues"
                        ],
                        "donts": [
                            "Don't expose network management interfaces to the public internet",
                            "Don't use default credentials for network devices",
                            "Don't neglect regular firmware updates for network infrastructure",
                            "Don't overlook the security of remote access solutions"
                        ]
                    },
                    "authentication": {
                        "summary": "This article highlights authentication vulnerabilities that could lead to account compromise. Organizations should strengthen their authentication mechanisms.",
                        "dos": [
                            "Implement multi-factor authentication for all user accounts",
                            "Use strong, unique passwords for each account or service",
                            "Consider adopting passwordless authentication methods where appropriate",
                            "Regularly audit user access rights and permissions"
                        ],
                        "donts": [
                            "Don't share account credentials between multiple users",
                            "Don't store passwords in plaintext or insecurely",
                            "Don't allow lengthy session durations without re-authentication",
                            "Don't rely solely on password-based authentication for sensitive systems"
                        ]
                    },
                    "encryption": {
                        "summary": "This article discusses encryption issues that could potentially expose sensitive data. Organizations should review their cryptographic implementations.",
                        "dos": [
                            "Use industry-standard encryption algorithms and protocols",
                            "Implement end-to-end encryption for sensitive communications",
                            "Properly manage encryption keys with secure storage and rotation",
                            "Encrypt data both in transit and at rest"
                        ],
                        "donts": [
                            "Don't use outdated or deprecated encryption algorithms",
                            "Don't implement custom cryptographic solutions without expert review",
                            "Don't store encryption keys alongside the encrypted data",
                            "Don't overlook encrypted backup solutions for sensitive data"
                        ]
                    },
                    "zero_day": {
                        "summary": "This article reveals details about a zero-day vulnerability with no available patch. Organizations should implement mitigations and closely monitor affected systems.",
                        "dos": [
                            "Implement recommended workarounds from security researchers or vendors",
                            "Monitor affected systems closely for signs of exploitation",
                            "Apply network-level protections to filter malicious traffic",
                            "Prepare incident response procedures in case of exploitation"
                        ],
                        "donts": [
                            "Don't ignore zero-day vulnerability announcements",
                            "Don't delay implementing mitigations where patches aren't available",
                            "Don't expose vulnerable systems directly to the internet",
                            "Don't wait for a patch before taking protective measures"
                        ]
                    },
                    "compliance": {
                        "summary": "This article addresses regulatory compliance issues in cybersecurity. Organizations should assess their practices to ensure they meet legal and industry requirements.",
                        "dos": [
                            "Maintain documentation of security controls and practices",
                            "Conduct regular compliance audits and assessments",
                            "Stay informed about regulatory changes affecting your industry",
                            "Implement data governance frameworks appropriate to your organization"
                        ],
                        "donts": [
                            "Don't ignore compliance deadlines or regulatory notifications",
                            "Don't collect more user data than necessary for business purposes",
                            "Don't overlook third-party vendor compliance requirements",
                            "Don't implement security controls without considering regulatory frameworks"
                        ]
                    },
                    "iot_security": {
                        "summary": "This article highlights security weaknesses in IoT devices that could be exploited. Users and organizations should take steps to secure their connected devices.",
                        "dos": [
                            "Change default passwords on all IoT devices immediately",
                            "Keep device firmware updated with the latest security patches",
                            "Isolate IoT devices on separate network segments",
                            "Disable unnecessary features and services on smart devices"
                        ],
                        "donts": [
                            "Don't connect sensitive IoT devices directly to the internet",
                            "Don't ignore security in favor of convenience when setting up devices",
                            "Don't leave unused IoT devices powered on and connected",
                            "Don't overlook physical security for important IoT installations"
                        ]
                    },
                    "cloud_security": {
                        "summary": "This article covers cloud security challenges that could lead to data exposure. Cloud service users should review their configurations to protect their assets.",
                        "dos": [
                            "Implement the principle of least privilege for cloud resource access",
                            "Enable multi-factor authentication for all cloud service accounts",
                            "Regularly audit cloud configurations for security misconfigurations",
                            "Use cloud security posture management tools to identify risks"
                        ],
                        "donts": [
                            "Don't leave cloud storage buckets publicly accessible",
                            "Don't hardcode credentials in application code or scripts",
                            "Don't overlook security responsibilities in your cloud service agreements",
                            "Don't neglect to encrypt sensitive data stored in the cloud"
                        ]
                    },
                    "mobile_security": {
                        "summary": "This article identifies security issues affecting mobile devices and applications. Users should take precautions to protect their mobile devices and data.",
                        "dos": [
                            "Keep mobile operating systems and apps updated with security patches",
                            "Only install applications from official app stores",
                            "Use biometric authentication where available",
                            "Encrypt sensitive data stored on mobile devices"
                        ],
                        "donts": [
                            "Don't jailbreak or root devices used for sensitive activities",
                            "Don't grant excessive permissions to mobile applications",
                            "Don't connect to untrusted public Wi-Fi networks without a VPN",
                            "Don't store sensitive unencrypted data on mobile devices"
                        ]
                    },
                    "general": {
                        "summary": "This article covers important cybersecurity topics that require attention. Following general security best practices can help mitigate these risks.",
                        "dos": [
                            "Keep all systems and software updated with security patches",
                            "Implement defense-in-depth security strategies with multiple protective layers",
                            "Regularly back up critical data following the 3-2-1 rule",
                            "Conduct regular security awareness training for all users"
                        ],
                        "donts": [
                            "Don't overlook basic security controls in favor of advanced solutions",
                            "Don't reuse credentials across different systems or services",
                            "Don't provide users with more access rights than necessary",
                            "Don't ignore security alerts or unusual system behavior"
                        ]
                    }
                }
                
                # Create article-specific tips based on identified categories
                if primary_category in category_tips:
                    better_tips = category_tips[primary_category].copy()
                    
                    # Customize the tips further based on article title and content
                    # Extract specific product or vendor names from title
                    import re
                    # Look for company/product names (often capitalized terms)
                    product_match = re.search(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b', title)
                    product_name = product_match.group(1) if product_match else None
                    
                    # Look for CVE numbers
                    cve_match = re.search(r'CVE-\d{4}-\d{4,}', title + " " + content if content else title)
                    cve_number = cve_match.group(0) if cve_match else None
                    
                    # Customize the summary with specific details if available
                    if product_name and primary_category == "vulnerability":
                        better_tips["summary"] = f"This article discusses critical vulnerabilities affecting {product_name} that could be exploited if left unaddressed. Users of these systems should apply security patches immediately."
                        better_tips["dos"][0] = f"Apply the latest security patches for {product_name} as soon as possible"
                        if cve_number:
                            better_tips["summary"] = f"This article reveals details about {cve_number}, a vulnerability affecting {product_name}. Users should apply patches to mitigate exploitation risks."
                            better_tips["dos"][2] = f"Monitor vendor advisories for {product_name} regarding {cve_number}"
                    elif product_name and primary_category == "malware":
                        better_tips["summary"] = f"This article discusses malware threats targeting {product_name} systems. Users should implement protective measures to safeguard against infection."
                        better_tips["dos"][0] = f"Ensure anti-malware solutions are updated and configured to protect {product_name} systems"
                    
                    # Add secondary category recommendations if available
                    if secondary_category and secondary_category in category_tips:
                        # Mix in some advice from the secondary category
                        better_tips["dos"] = better_tips["dos"][:3] + [category_tips[secondary_category]["dos"][0]]
                        better_tips["donts"] = better_tips["donts"][:3] + [category_tips[secondary_category]["donts"][0]]
                else:
                    # Fallback to general tips with customization
                    better_tips = category_tips["general"].copy()
                    
                    # Extract keywords for customization
                    key_terms = []
                    if title:
                        # Look for technical terms or significant words in title
                        words = title.split()
                        for word in words:
                            if len(word) > 4 and word[0].isupper():
                                key_terms.append(word)
                    
                    if key_terms:
                        term_phrase = ", ".join(key_terms[:2])
                        better_tips["summary"] = f"This article discusses cybersecurity issues related to {term_phrase}. Following security best practices can help mitigate associated risks."
                
                # Update or create tips document
                if tips:
                    # Update existing document
                    update_one(tips_collection, {"_id": tips.get("_id")}, {"tips": better_tips})
                else:
                    # Create new document
                    new_tips = {
                        "article_id": article_id,
                        "title": title,
                        "source": article.get('source', 'Unknown'),
                        "date": article.get('date', 'Unknown'),
                        "source_type": article.get('source_type', article.get('source', 'unknown').lower().replace(' ', '')),
                        "tips": better_tips,
                        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    # Add _id field for Firestore document ID
                    new_tips["_id"] = article_id
                    update_one(tips_collection, {"_id": article_id}, new_tips, upsert=True)
                
                updates_count += 1
                print(f"Updated tips for article: {title} with {primary_category} category" + 
                      (f" and {secondary_category} category" if secondary_category else ""))
        
        # Close Firebase connection
        close()
        
        print(f"\nUpdated {updates_count} tips with article-specific content")
        return True
        
    except Exception as e:
        print(f"Error updating placeholder tips: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Updating Placeholder Tips ===")
    success = update_placeholder_tips()
    if success:
        print("Tips update completed successfully")
    else:
        print("Failed to update tips")
        sys.exit(1) 